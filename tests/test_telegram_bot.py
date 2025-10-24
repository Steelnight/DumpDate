"""
Tests for the main Telegram bot conversation handlers.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import Update, User, Message, Chat
from telegram.ext import ConversationHandler, ContextTypes

from telegram_bot.bot import (
    ADDRESS,
    CONFIRM_ADDRESS,
    NOTIFICATION_TIME,
    SELECT_SUB,
    subscribe,
    handle_address_input,
    confirm_address,
    set_notification_time,
    unsubscribe,
    select_sub_to_unsubscribe,
    my_subscriptions
)


@pytest.fixture
def mock_update():
    """Returns a mock Telegram Update object."""
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.chat = MagicMock(spec=Chat)
    update.message.chat_id = 12345
    update.message.from_user = MagicMock(spec=User)
    update.message.from_user.id = 12345
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Returns a mock Telegram ContextTypes.DEFAULT_TYPE object."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    return context


@pytest.fixture
def mock_facade():
    """Fixture to mock the WasteManagementFacade."""
    with patch('telegram_bot.bot.facade', autospec=True) as mock_facade:
        yield mock_facade


@pytest.mark.asyncio
async def test_subscribe_starts_conversation(mock_update, mock_context):
    """Tests that the /subscribe command starts the conversation."""
    result = await subscribe(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_with("Bitte gib deine Adresse ein (z.B. 'Test Straße 1').")
    assert result == ADDRESS


@pytest.mark.asyncio
async def test_handle_address_input_no_matches(mock_update, mock_context, mock_facade):
    """Tests address input with no matches found."""
    mock_facade.find_address_matches.return_value = []
    mock_update.message.text = "Unknown Street 123"
    result = await handle_address_input(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_with("Leider konnte keine passende Adresse gefunden werden. Bitte versuche es erneut.")
    assert result == ADDRESS


@pytest.mark.asyncio
async def test_handle_address_input_with_matches(mock_update, mock_context, mock_facade):
    """Tests address input with matches found."""
    matches = [("Test Straße 1", 1), ("Test Straße 2", 2)]
    mock_facade.find_address_matches.return_value = matches
    mock_update.message.text = "Test Straße"
    result = await handle_address_input(mock_update, mock_context)
    assert result == CONFIRM_ADDRESS


@pytest.mark.asyncio
async def test_confirm_address_invalid_selection(mock_update, mock_context, mock_facade):
    """Tests address confirmation with an invalid selection."""
    mock_context.user_data["matches"] = {"Test Straße 1": 1}
    mock_update.message.text = "Invalid Selection"
    result = await confirm_address(mock_update, mock_context)
    assert result == CONFIRM_ADDRESS


@pytest.mark.asyncio
async def test_confirm_address_valid_selection(mock_update, mock_context, mock_facade):
    """Tests address confirmation with a valid selection."""
    mock_context.user_data["matches"] = {"Test Straße 1": 1}
    mock_update.message.text = "Test Straße 1"
    result = await confirm_address(mock_update, mock_context)
    assert result == NOTIFICATION_TIME


@pytest.mark.asyncio
async def test_set_notification_time_evening(mock_update, mock_context, mock_facade):
    """Tests setting the notification time to evening."""
    mock_context.user_data["selected_address_str"] = "Test Straße 1"
    mock_update.message.text = "Abend vorher (19 Uhr)"
    result = await set_notification_time(mock_update, mock_context)
    mock_facade.subscribe_address_for_user.assert_called_with(
        chat_id=12345, address="Test Straße 1", notification_time="evening"
    )
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_set_notification_time_morning(mock_update, mock_context, mock_facade):
    """Tests setting the notification time to morning."""
    mock_context.user_data["selected_address_str"] = "Test Straße 1"
    mock_update.message.text = "Morgen der Abholung (6 Uhr)"
    result = await set_notification_time(mock_update, mock_context)
    mock_facade.subscribe_address_for_user.assert_called_with(
        chat_id=12345, address="Test Straße 1", notification_time="morning"
    )
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_my_subscriptions_no_subscriptions(mock_update, mock_context, mock_facade):
    """Tests that the /mysubscriptions command handles no subscriptions."""
    mock_facade.get_user_subscriptions.return_value = []
    await my_subscriptions(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_with("Du hast keine aktiven Benachrichtigungen.")


@pytest.mark.asyncio
async def test_my_subscriptions_with_subscriptions(mock_update, mock_context, mock_facade):
    """Tests that the /mysubscriptions command displays subscriptions."""
    subscriptions = [{"id": 1, "address_id": 1, "notification_time": "evening"}]
    mock_facade.get_user_subscriptions.return_value = subscriptions
    mock_facade.get_address_by_id.return_value = "Test Straße 1"
    await my_subscriptions(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_with(
        "Deine aktiven Benachrichtigungen:\n\n- Test Straße 1 (Abend vorher)\n"
    )


@pytest.mark.asyncio
async def test_unsubscribe_no_subscriptions(mock_update, mock_context, mock_facade):
    """Tests that the /unsubscribe command handles no subscriptions."""
    mock_facade.get_user_subscriptions.return_value = []
    result = await unsubscribe(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_with("Du hast keine aktiven Benachrichtigungen zum Abbestellen.")
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_unsubscribe_starts_conversation(mock_update, mock_context, mock_facade):
    """Tests that the /unsubscribe command starts the conversation."""
    subscriptions = [{"id": 1, "address_id": 1}]
    mock_facade.get_user_subscriptions.return_value = subscriptions
    mock_facade.get_address_by_id.return_value = "Test Straße 1"
    result = await unsubscribe(mock_update, mock_context)
    assert result == SELECT_SUB


@pytest.mark.asyncio
async def test_select_sub_to_unsubscribe_invalid_selection(mock_update, mock_context, mock_facade):
    """Tests unsubscribing with an invalid selection."""
    mock_context.user_data["subscriptions"] = {"Test Straße 1": 1}
    mock_update.message.text = "Invalid Selection"
    result = await select_sub_to_unsubscribe(mock_update, mock_context)
    assert result == SELECT_SUB


@pytest.mark.asyncio
async def test_select_sub_to_unsubscribe_valid_selection(mock_update, mock_context, mock_facade):
    """Tests unsubscribing with a valid selection."""
    mock_context.user_data["subscriptions"] = {"Test Straße 1": 1}
    mock_update.message.text = "Test Straße 1"
    result = await select_sub_to_unsubscribe(mock_update, mock_context)
    mock_facade.unsubscribe.assert_called_with(1)
    assert result == ConversationHandler.END
