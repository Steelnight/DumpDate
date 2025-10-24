"""
This module contains the main logic for the Telegram bot, refactored to use the WasteManagementFacade.
"""
import logging
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Import services and facade
from schedule_parser.services.address_service import AddressService
from schedule_parser.services.persistence_service import PersistenceService
from schedule_parser.services.schedule_service import ScheduleService
from schedule_parser.services.subscription_service import SubscriptionService
from schedule_parser.services.notification_service import NotificationService
from schedule_parser.facade import WasteManagementFacade
from schedule_parser.exceptions import DownloadError, ParsingError

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# States for conversation
ADDRESS, CONFIRM_ADDRESS, NOTIFICATION_TIME, SELECT_SUB = range(4)

# --- Facade Initialization ---
# In a real application, this would be better managed with a dependency injection container.
address_service = AddressService()
persistence_service = PersistenceService()
schedule_service = ScheduleService()
subscription_service = SubscriptionService(persistence_service)
notification_service = NotificationService(persistence_service)

facade = WasteManagementFacade(
    address_service=address_service,
    schedule_service=schedule_service,
    persistence_service=persistence_service,
    subscription_service=subscription_service,
    notification_service=notification_service,
)
# --- End Facade Initialization ---


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message."""
    await update.message.reply_text(
        "Hallo! Ich bin der DumpDate-Bot. Nutze /subscribe, um eine neue Adresse zu abonnieren."
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the subscription conversation."""
    await update.message.reply_text("Bitte gib deine Adresse ein (z.B. 'Test Straße 1').")
    return ADDRESS

async def handle_address_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's address input and suggests matches."""
    try:
        matches = facade.find_address_matches(update.message.text)
        if not matches:
            await update.message.reply_text("Leider konnte keine passende Adresse gefunden werden. Bitte versuche es erneut.")
            return ADDRESS

        context.user_data["matches"] = {match[0]: match[1] for match in matches} # Store as dict {address_str: address_id}

        reply_keyboard = [[match[0]] for match in matches]
        await update.message.reply_text(
            "Ich habe folgende Adressen gefunden. Bitte wähle die richtige aus:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return CONFIRM_ADDRESS
    except FileNotFoundError:
        await update.message.reply_text("Fehler: Die Adress-Datenbank wurde nicht gefunden. Bitte den Administrator informieren.")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in handle_address_input: {e}")
        await update.message.reply_text("Ein unerwarteter Fehler ist aufgetreten. Bitte versuche es später erneut.")
        return ConversationHandler.END


async def confirm_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles address confirmation and asks for notification time."""
    selected_address = update.message.text
    matches = context.user_data.get("matches", {})

    if selected_address not in matches:
        await update.message.reply_text("Ungültige Auswahl. Bitte wähle eine der vorgeschlagenen Adressen.")
        # Resend options
        reply_keyboard = [[addr] for addr in matches.keys()]
        await update.message.reply_text(
            "Bitte wähle die richtige aus:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return CONFIRM_ADDRESS

    context.user_data["selected_address_str"] = selected_address
    context.user_data["selected_address_id"] = matches[selected_address]

    reply_keyboard = [["Abend vorher (19 Uhr)", "Morgen der Abholung (6 Uhr)"]]
    await update.message.reply_text(
        "Wann möchtest du benachrichtigt werden?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return NOTIFICATION_TIME

async def set_notification_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles notification time, triggers the facade, and ends the conversation."""
    notification_choice = update.message.text
    notification_time = "evening" if "Abend" in notification_choice else "morning"
    chat_id = update.message.chat_id
    address_str = context.user_data["selected_address_str"]

    await update.message.reply_text(f"Richte Abonnement für '{address_str}' ein. Das kann einen Moment dauern...", reply_markup=ReplyKeyboardRemove())

    try:
        success = facade.subscribe_address_for_user(
            chat_id=chat_id,
            address=address_str,
            notification_time=notification_time,
        )
        if success:
            await update.message.reply_text("Abonnement erfolgreich eingerichtet!")
        else:
            await update.message.reply_text("Ein interner Fehler hat die Einrichtung verhindert. Bitte versuche es später erneut.")
    except (ValueError, FileNotFoundError) as e:
         await update.message.reply_text(f"Fehler: {e}")
    except DownloadError:
        await update.message.reply_text("Fehler beim Herunterladen des Abfallkalenders. Bitte versuche es später erneut.")
    except ParsingError:
        await update.message.reply_text("Fehler beim Verarbeiten des Abfallkalenders. Bitte den Administrator informieren.")
    except Exception as e:
        logger.error(f"Unexpected error in set_notification_time: {e}")
        await update.message.reply_text("Ein unerwarteter Fehler ist aufgetreten.")

    context.user_data.clear()
    return ConversationHandler.END

async def my_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the user's current subscriptions."""
    chat_id = update.message.chat_id
    subscriptions = facade.get_user_subscriptions(chat_id)
    if not subscriptions:
        await update.message.reply_text("Du hast keine aktiven Benachrichtigungen.")
        return

    message = "Deine aktiven Benachrichtigungen:\n\n"
    for sub in subscriptions:
        address = facade.get_address_by_id(sub["address_id"])
        time_str = "Abend vorher" if sub["notification_time"] == "evening" else "Morgen der Abholung"
        message += f"- {address} ({time_str})\n"
    await update.message.reply_text(message)

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the unsubscribe conversation."""
    chat_id = update.message.chat_id
    subscriptions = facade.get_user_subscriptions(chat_id)
    if not subscriptions:
        await update.message.reply_text("Du hast keine aktiven Benachrichtigungen zum Abbestellen.")
        return ConversationHandler.END

    context.user_data["subscriptions"] = {f"{facade.get_address_by_id(sub['address_id'])}": sub['id'] for sub in subscriptions}

    reply_keyboard = [[address] for address in context.user_data["subscriptions"].keys()]
    await update.message.reply_text(
        "Wähle eine Benachrichtigung zum Abbestellen aus:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return SELECT_SUB

async def select_sub_to_unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the selection of a subscription to unsubscribe from."""
    selected_address = update.message.text
    sub_id = context.user_data.get("subscriptions", {}).get(selected_address)

    if not sub_id:
        await update.message.reply_text("Ungültige Auswahl. Bitte wähle eine der Optionen.")
        return SELECT_SUB

    success = facade.unsubscribe(sub_id)
    if success:
        await update.message.reply_text("Benachrichtigung erfolgreich abbestellt.", reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text("Ein Fehler ist beim Abbestellen aufgetreten.", reply_markup=ReplyKeyboardRemove())

    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text("Vorgang abgebrochen.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END


async def next_pickup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the next pickup for each of the user's subscriptions."""
    chat_id = update.message.chat_id
    pickups = facade.get_next_pickup_for_user(chat_id)

    if not pickups:
        await update.message.reply_text("Du hast keine aktiven Abonnements oder es stehen keine Abholungen an.")
        return

    message = "<b>Nächste Abholungen:</b>\n\n"
    for pickup in pickups:
        address = pickup['address']
        event = pickup['event']
        # Simple emoji mapping
        emoji_map = {
            "Restabfall": "⚫",
            "Bioabfall": "🟤",
            "Papier": "🔵",
            "Gelbe Tonne": "🟡",
        }
        emoji = emoji_map.get(event['waste_type'], "🗑️")
        message += f"📍 <b>{address}</b>\n"
        message += f"   {emoji} {event['waste_type']} am {event['date']}\n\n"

    await update.message.reply_text(message, parse_mode='HTML')


def main(bot_token: str, application: Application = None) -> None:
    """Start the bot."""
    if not application:
        application = Application.builder().token(bot_token).build()

    # Subscription Conversation
    subscribe_conv = ConversationHandler(
        entry_points=[CommandHandler("subscribe", subscribe)],
        states={
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_address_input)],
            CONFIRM_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_address)],
            NOTIFICATION_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_notification_time)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Unsubscribe Conversation
    unsubscribe_conv = ConversationHandler(
        entry_points=[CommandHandler("unsubscribe", unsubscribe)],
        states={
            SELECT_SUB: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_sub_to_unsubscribe)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mysubscriptions", my_subscriptions))
    application.add_handler(CommandHandler("nextpickup", next_pickup))
    application.add_handler(subscribe_conv)
    application.add_handler(unsubscribe_conv)

    if __name__ == "__main__":
        application.run_polling()
