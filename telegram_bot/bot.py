"""
This module contains the main logic for the Telegram bot, refactored to use the WasteManagementFacade.
"""

import asyncio
import logging
import sqlite3
from datetime import datetime

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (AIORateLimiter, Application, CommandHandler,
                          ContextTypes, ConversationHandler, MessageHandler,
                          filters)

from schedule_parser.config import (TELEGRAM_BOT_TOKEN,
                                    TELEGRAM_RATE_LIMIT_GROUP,
                                    TELEGRAM_RATE_LIMIT_OVERALL,
                                    TELEGRAM_RATE_LIMIT_PER_CHAT,
                                    WASTE_SCHEDULE_DB_PATH)
from schedule_parser.exceptions import DownloadError, ParsingError
# Import services and facade
from schedule_parser.facade import WasteManagementFacade

from .context import CustomContext
from .scheduler import scheduler

logger = logging.getLogger(__name__)

# States for conversation
# ADDRESS removed. New flow: LOCATION_ID -> NAME_CHOICE -> (CUSTOM_NAME) -> NOTIFICATION_TIME
LOCATION_ID, NAME_CHOICE, CUSTOM_NAME, NOTIFICATION_TIME, SELECT_SUB = range(5)

Context = CustomContext


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message."""
    await update.message.reply_text(
        "Hallo! Ich bin der DumpDate-Bot. Nutze /subscribe, um einen neuen Standort zu abonnieren."
    )


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the subscription conversation."""
    await update.message.reply_text(
        "Bitte gib die Standort-ID ein (z.B. 54367).\n"
        "Die ID findest du über die Webseite der Stadt Dresden oder wie in der Dokumentation beschrieben."
    )
    return LOCATION_ID


async def handle_location_id_input(update: Update, context: Context) -> int:
    """Handles the user's location ID input and verifies it."""
    try:
        location_id_str = update.message.text.strip()
        if not location_id_str.isdigit():
             await update.message.reply_text(
                "Bitte gib eine gültige Zahl als Standort-ID ein."
            )
             return LOCATION_ID

        location_id = int(location_id_str)

        await update.message.reply_text("Überprüfe ID...")

        # Verify and fetch address name
        address_name = context.facade.verify_location_id(location_id)

        if not address_name:
            await update.message.reply_text(
                "Die ID konnte nicht verifiziert werden oder es wurden keine Daten gefunden. "
                "Bitte überprüfe die ID und versuche es erneut."
            )
            return LOCATION_ID

        context.user_data["selected_location_id"] = location_id
        context.user_data["detected_address_name"] = address_name

        reply_keyboard = [["Ja, behalten", "Nein, ändern"]]
        await update.message.reply_text(
            f"Gefundene Adresse: '{address_name}'.\nMöchtest du diesen Namen behalten?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return NAME_CHOICE

    except Exception as e:
        logger.error(f"Error in handle_location_id_input: {e}")
        await update.message.reply_text(
            "Ein unerwarteter Fehler ist aufgetreten. Bitte versuche es später erneut."
        )
        return ConversationHandler.END


async def handle_name_choice(update: Update, context: Context) -> int:
    """Handles the user's choice about the address name."""
    choice = update.message.text

    if choice == "Ja, behalten":
        context.user_data["final_address_name"] = context.user_data["detected_address_name"]
        return await ask_notification_time(update, context)
    elif choice == "Nein, ändern":
        await update.message.reply_text(
            "Bitte gib den gewünschten Namen für diesen Standort ein:",
            reply_markup=ReplyKeyboardRemove()
        )
        return CUSTOM_NAME
    else:
        await update.message.reply_text(
            "Bitte wähle eine der Optionen.",
             reply_markup=ReplyKeyboardMarkup([["Ja, behalten", "Nein, ändern"]], one_time_keyboard=True)
        )
        return NAME_CHOICE

async def handle_custom_name(update: Update, context: Context) -> int:
    """Handles the input of a custom name."""
    custom_name = update.message.text.strip()
    if not custom_name:
         await update.message.reply_text("Der Name darf nicht leer sein. Bitte versuche es erneut.")
         return CUSTOM_NAME

    context.user_data["final_address_name"] = custom_name
    return await ask_notification_time(update, context)


async def ask_notification_time(update: Update, context: Context) -> int:
    """Asks for notification time."""
    reply_keyboard = [["Abend vorher (19 Uhr)", "Morgen der Abholung (6 Uhr)"]]
    await update.message.reply_text(
        "Wann möchtest du benachrichtigt werden?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return NOTIFICATION_TIME


async def set_notification_time(update: Update, context: Context) -> int:
    """Handles notification time, triggers the facade, and ends the conversation."""
    notification_choice = update.message.text
    notification_time = "evening" if "Abend" in notification_choice else "morning"
    chat_id = update.message.chat_id

    location_id = context.user_data["selected_location_id"]
    address_name = context.user_data["final_address_name"]

    await update.message.reply_text(
        f"Richte Abonnement für '{address_name}' (ID: {location_id}) ein...",
        reply_markup=ReplyKeyboardRemove(),
    )

    try:
        success = context.facade.subscribe_address_for_user(
            chat_id=chat_id,
            address_id=location_id,
            address_name=address_name,
            notification_time=notification_time,
        )
        if success:
            await update.message.reply_text("Abonnement erfolgreich eingerichtet!")
        else:
            await update.message.reply_text(
                "Ein interner Fehler hat die Einrichtung verhindert. Bitte versuche es später erneut."
            )
    except (ValueError, FileNotFoundError) as e:
        await update.message.reply_text(f"Fehler: {e}")
    except DownloadError:
        await update.message.reply_text(
            "Fehler beim Herunterladen des Abfallkalenders. Bitte versuche es später erneut."
        )
    except ParsingError:
        await update.message.reply_text(
            "Fehler beim Verarbeiten des Abfallkalenders. Bitte den Administrator informieren."
        )
    except Exception as e:
        logger.error(f"Unexpected error in set_notification_time: {e}")
        await update.message.reply_text("Ein unerwarteter Fehler ist aufgetreten.")

    context.user_data.clear()
    return ConversationHandler.END


async def my_subscriptions(update: Update, context: Context) -> None:
    """Displays the user's current subscriptions."""
    chat_id = update.message.chat_id
    subscriptions = context.facade.get_user_subscriptions(chat_id)
    if not subscriptions:
        await update.message.reply_text("Du hast keine aktiven Benachrichtigungen.")
        return

    message = "Deine aktiven Benachrichtigungen:\n\n"
    for sub in subscriptions:
        # Use address_name if available, otherwise fetch from ID (or fallback)
        address = sub["address_name"] or context.facade.get_address_by_id(sub["address_id"])
        time_str = (
            "Abend vorher"
            if sub["notification_time"] == "evening"
            else "Morgen der Abholung"
        )
        message += f"- {address} ({time_str})\n"
    await update.message.reply_text(message)


async def unsubscribe(update: Update, context: Context) -> int:
    """Starts the unsubscribe conversation."""
    chat_id = update.message.chat_id
    subscriptions = context.facade.get_user_subscriptions(chat_id)
    if not subscriptions:
        await update.message.reply_text(
            "Du hast keine aktiven Benachrichtigungen zum Abbestellen."
        )
        return ConversationHandler.END

    context.user_data["subscriptions"] = {
        f"{sub['address_name'] or context.facade.get_address_by_id(sub['address_id'])}": sub["id"]
        for sub in subscriptions
    }

    reply_keyboard = [
        [address] for address in context.user_data["subscriptions"].keys()
    ]
    await update.message.reply_text(
        "Wähle eine Benachrichtigung zum Abbestellen aus:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return SELECT_SUB


async def select_sub_to_unsubscribe(update: Update, context: Context) -> int:
    """Handles the selection of a subscription to unsubscribe from."""
    selected_address = update.message.text
    sub_id = context.user_data.get("subscriptions", {}).get(selected_address)

    if not sub_id:
        await update.message.reply_text(
            "Ungültige Auswahl. Bitte wähle eine der Optionen."
        )
        return SELECT_SUB

    success = context.facade.unsubscribe(sub_id)
    if success:
        await update.message.reply_text(
            "Benachrichtigung erfolgreich abbestellt.",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await update.message.reply_text(
            "Ein Fehler ist beim Abbestellen aufgetreten.",
            reply_markup=ReplyKeyboardRemove(),
        )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text(
        "Vorgang abgebrochen.", reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END


async def next_pickup(update: Update, context: Context) -> None:
    """Displays the next pickup for each of the user's subscriptions."""
    chat_id = update.message.chat_id
    pickups = context.facade.get_next_pickup_for_user(chat_id)

    if not pickups:
        await update.message.reply_text(
            "Du hast keine aktiven Abonnements oder es stehen keine Abholungen an."
        )
        return

    message = "<b>Nächste Abholungen:</b>\n\n"
    for pickup in pickups:
        address = pickup["address"]
        event = pickup["event"]
        # Simple emoji mapping
        emoji_map = {
            "Restabfall": "⚫",
            "Bioabfall": "🟤",
            "Papier": "🔵",
            "Gelbe Tonne": "🟡",
        }
        emoji = emoji_map.get(event["waste_type"], "🗑️")
        message += f"📍 <b>{address}</b>\n"
        message += f"   {emoji} {event['waste_type']} am {event['date']}\n\n"

    await update.message.reply_text(message, parse_mode="HTML")


def setup_handlers(application: Application) -> None:
    """Start the bot."""

    # Subscription Conversation
    subscribe_conv = ConversationHandler(
        entry_points=[CommandHandler("subscribe", subscribe)],
        states={
            LOCATION_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_location_id_input)
            ],
            NAME_CHOICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_choice)
            ],
            CUSTOM_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_name)
            ],
            NOTIFICATION_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_notification_time)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Unsubscribe Conversation
    unsubscribe_conv = ConversationHandler(
        entry_points=[CommandHandler("unsubscribe", unsubscribe)],
        states={
            SELECT_SUB: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, select_sub_to_unsubscribe
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mysubscriptions", my_subscriptions))
    application.add_handler(CommandHandler("nextpickup", next_pickup))
    application.add_handler(subscribe_conv)
    application.add_handler(unsubscribe_conv)


def record_bot_start_time(facade_instance: WasteManagementFacade):
    """Records the bot's start time in the system_info table."""
    try:
        facade_instance.persistence_service.record_system_info(
            "bot_start_time", datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Failed to record bot start time: {e}")


async def main(facade_instance: WasteManagementFacade):
    """Initializes and runs the bot and scheduler."""
     # Record the bot start time
    record_bot_start_time(facade_instance)

    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set.")
        return

    # Configure rate limiting
    rate_limiter = AIORateLimiter(
        overall_max_rate=TELEGRAM_RATE_LIMIT_OVERALL,
        group_max_rate=TELEGRAM_RATE_LIMIT_GROUP,
    )

    context_types = ContextTypes(context=Context)
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .rate_limiter(rate_limiter)
        .context_types(context_types)
        .build()
    )

    # Set the facade on the application's context
    application.context_types.context.facade = facade_instance

    # Setup handlers in bot_main
    setup_handlers(application)

    # Manually start the application
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    logger.info("Bot started and polling...")

    # Run the schedulers and bot polling concurrently
    try:
        await asyncio.gather(
            scheduler(facade_instance, application),
            facade_instance.smart_schedule_service.run_scheduler(),
        )
    except asyncio.CancelledError:
        logger.info("Bot is stopping...")
    finally:
        # Gracefully stop the application
        if application.updater.running:
            await application.updater.stop()
        if application.running:
            await application.stop()
            await application.shutdown()
