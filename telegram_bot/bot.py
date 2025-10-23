"""
This module contains the main logic for the Telegram bot.
"""
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from .address_matcher import find_address_matches, get_address_by_id
from .subscription_manager import add_subscription, get_subscriptions, remove_subscription

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# States for conversation
ADDRESS, CONFIRM_ADDRESS, NOTIFICATION_TIME = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "Hallo, ich bin der DumpDate-Bot und kann dir Benachrichtigungen zur Abholung deiner Mülltonnen bereitstellen. "
        "Nutze /subscribe um Benachrichtigungen einzurichten."
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the subscription conversation and asks for an address."""
    await update.message.reply_text("Bitte gib deine Adresse ein, um Benachrichtigungen einzurichten.")
    return ADDRESS

async def address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the address and asks for confirmation."""
    matches = find_address_matches(update.message.text)
    if not matches:
        await update.message.reply_text("Leider konnte keine passende Adresse gefunden werden. Bitte versuche es erneut.")
        return ADDRESS

    context.user_data["matches"] = matches

    if len(matches) == 1:
        context.user_data["selected_address"] = matches[0]
        reply_keyboard = [["Ja", "Nein"]]
        await update.message.reply_text(
            f"Ich habe folgende Adresse gefunden: {matches[0][0]}. Ist das korrekt?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return CONFIRM_ADDRESS
    else:
        reply_keyboard = [[match[0]] for match in matches]
        await update.message.reply_text(
            "Ich habe mehrere mögliche Adressen gefunden. Bitte wähle die richtige aus:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return CONFIRM_ADDRESS

async def confirm_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles address confirmation and asks for notification time."""
    response = update.message.text
    if "selected_address" in context.user_data: # Single match confirmation
        if response.lower() == "ja":
            pass # Address is already set
        else:
            await update.message.reply_text("Ok, bitte gib die Adresse erneut ein.")
            return ADDRESS
    else: # Multiple matches selection
        selected_address_str = response
        matches = context.user_data.get("matches", [])
        selected_address = next((match for match in matches if match[0] == selected_address_str), None)

        if not selected_address:
            await update.message.reply_text("Ungültige Auswahl. Bitte wähle eine der vorgeschlagenen Adressen.")
            return CONFIRM_ADDRESS

        context.user_data["selected_address"] = selected_address

    reply_keyboard = [["Abend vorher (19 Uhr)", "Morgen der Abholung (6 Uhr)"]]
    await update.message.reply_text(
        "Wann möchtest du benachrichtigt werden?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return NOTIFICATION_TIME

async def notification_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles notification time and ends the conversation."""
    response = update.message.text
    notification_time = "evening" if "Abend" in response else "morning"

    chat_id = update.message.chat_id
    address_id = context.user_data["selected_address"][1]

    add_subscription(chat_id, address_id, notification_time)

    await update.message.reply_text("Abonnement erfolgreich eingerichtet!")
    await update.message.reply_text("Das ist die Testnachricht, es ist alles für die Adresse eingerichtet.")

    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text("Abonnement-Vorgang abgebrochen.")
    context.user_data.clear()
    return ConversationHandler.END

def main(bot_token: str, application: Application = None) -> None:
    """Start the bot."""
    if not application:
        application = Application.builder().token(bot_token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("subscribe", subscribe)],
        states={
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, address)],
            CONFIRM_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_address)],
            NOTIFICATION_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, notification_time)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("mysubscriptions", my_subscriptions))

    # Unsubscribe conversation handler
    SELECT_SUB_STATE, = range(1)
    unsubscribe_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("unsubscribe", unsubscribe)],
        states={
            SELECT_SUB_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_sub)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(unsubscribe_conv_handler)

    # If the application is passed in, don't run polling here
    if __name__ == "__main__":
        # Run the bot until the user presses Ctrl-C
        application.run_polling()

async def my_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the user's current subscriptions."""
    chat_id = update.message.chat_id
    subscriptions = get_subscriptions(chat_id)
    if not subscriptions:
        await update.message.reply_text("Du hast keine aktiven Benachrichtigungen.")
        return

    message = "Deine aktiven Benachrichtigungen:\n\n"
    for sub_id, address_id, notification_time in subscriptions:
        address = get_address_by_id(address_id)
        time_str = "Abend vorher (19 Uhr)" if notification_time == "evening" else "Morgen der Abholung (6 Uhr)"
        message += f"- {address} ({time_str})\n"

    await update.message.reply_text(message)

# Unsubscribe conversation
SELECT_SUB, CONFIRM_UNSUBSCRIBE = range(2)

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the unsubscribe conversation."""
    chat_id = update.message.chat_id
    subscriptions = get_subscriptions(chat_id)
    if not subscriptions:
        await update.message.reply_text("Du hast keine aktiven Benachrichtigungen zum Abbestellen.")
        return ConversationHandler.END

    context.user_data["subscriptions"] = subscriptions
    reply_keyboard = []
    for sub_id, address_id, _ in subscriptions:
        address = get_address_by_id(address_id)
        reply_keyboard.append([f"{address} (ID: {sub_id})"])

    await update.message.reply_text(
        "Wähle eine Benachrichtigung zum Abbestellen aus:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return SELECT_SUB

async def select_sub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the selection of a subscription to unsubscribe from."""
    selected_option = update.message.text
    try:
        sub_id = int(selected_option.split("(ID: ")[1].replace(")", ""))
    except (IndexError, ValueError):
        await update.message.reply_text("Ungültige Auswahl. Bitte wähle eine der Optionen.")
        return SELECT_SUB

    context.user_data["selected_sub_id"] = sub_id
    remove_subscription(sub_id)
    await update.message.reply_text("Benachrichtigung erfolgreich abbestellt.")
    return ConversationHandler.END
