"""
Unit tests for the Telegram bot logic.
"""

from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from telegram import Chat, Message, Update, User
from telegram.ext import ContextTypes

from telegram_bot.bot import (
    LOCATION_ID,
    NAME_CHOICE,
    CUSTOM_NAME,
    NOTIFICATION_TIME,
    handle_location_id_input,
    handle_name_choice,
    handle_custom_name,
    set_notification_time,
    start,
    subscribe,
)

# Mock constants
CHAT_ID = 12345
USER_ID = 67890
USERNAME = "testuser"
TEST_ADDRESS_ID = 54367
TEST_ADDRESS_NAME = "Chemnitzer Straße 42"

@pytest.fixture
def update():
    """Creates a mock Update object."""
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.chat_id = CHAT_ID
    update.message.from_user = MagicMock(spec=User)
    update.message.from_user.id = USER_ID
    update.message.from_user.username = USERNAME
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def context():
    """Creates a mock Context object with the facade."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    context.facade = MagicMock()
    return context


@pytest.mark.asyncio
async def test_start(update, context):
    """Tests the start command."""
    await start(update, context)
    update.message.reply_text.assert_called_once()
    assert "DumpDate-Bot" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_subscribe_starts_conversation(update, context):
    """Tests that /subscribe starts the conversation and asks for Location ID."""
    state = await subscribe(update, context)
    assert state == LOCATION_ID
    update.message.reply_text.assert_called_once()
    assert "Standort-ID" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_location_id_valid(update, context):
    """Tests handling a valid location ID input."""
    update.message.text = str(TEST_ADDRESS_ID)
    context.facade.verify_location_id.return_value = TEST_ADDRESS_NAME

    state = await handle_location_id_input(update, context)

    assert state == NAME_CHOICE
    context.facade.verify_location_id.assert_called_once_with(TEST_ADDRESS_ID)
    assert context.user_data["selected_location_id"] == TEST_ADDRESS_ID
    assert context.user_data["detected_address_name"] == TEST_ADDRESS_NAME
    # Verify it asks for confirmation
    args = update.message.reply_text.call_args_list[-1]
    assert TEST_ADDRESS_NAME in args[0][0]
    assert "Möchtest du diesen Namen behalten?" in args[0][0]


@pytest.mark.asyncio
async def test_handle_location_id_invalid_number(update, context):
    """Tests handling an invalid (non-numeric) location ID."""
    update.message.text = "invalid-id"

    state = await handle_location_id_input(update, context)

    assert state == LOCATION_ID
    update.message.reply_text.assert_called_with("Bitte gib eine gültige Zahl als Standort-ID ein.")


@pytest.mark.asyncio
async def test_handle_location_id_not_found(update, context):
    """Tests handling a valid number but invalid ID (not found)."""
    update.message.text = "99999"
    context.facade.verify_location_id.return_value = None

    state = await handle_location_id_input(update, context)

    assert state == LOCATION_ID
    context.facade.verify_location_id.assert_called_once_with(99999)
    assert "nicht verifiziert werden" in update.message.reply_text.call_args_list[-1][0][0]


@pytest.mark.asyncio
async def test_handle_name_choice_keep(update, context):
    """Tests choosing to keep the detected name."""
    update.message.text = "Ja, behalten"
    context.user_data["selected_location_id"] = TEST_ADDRESS_ID
    context.user_data["detected_address_name"] = TEST_ADDRESS_NAME

    state = await handle_name_choice(update, context)

    assert state == NOTIFICATION_TIME
    assert context.user_data["final_address_name"] == TEST_ADDRESS_NAME
    update.message.reply_text.assert_called_with(
        "Wann möchtest du benachrichtigt werden?",
        reply_markup=ANY
    )

@pytest.mark.asyncio
async def test_handle_name_choice_change(update, context):
    """Tests choosing to change the name."""
    update.message.text = "Nein, ändern"
    context.user_data["selected_location_id"] = TEST_ADDRESS_ID
    context.user_data["detected_address_name"] = TEST_ADDRESS_NAME

    state = await handle_name_choice(update, context)

    assert state == CUSTOM_NAME
    update.message.reply_text.assert_called()
    assert "gewünschten Namen" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_custom_name(update, context):
    """Tests entering a custom name."""
    update.message.text = "My Custom Home"

    state = await handle_custom_name(update, context)

    assert state == NOTIFICATION_TIME
    assert context.user_data["final_address_name"] == "My Custom Home"


@pytest.mark.asyncio
async def test_set_notification_time_success(update, context):
    """Tests setting the notification time and finalizing subscription."""
    update.message.text = "Abend vorher (19 Uhr)"
    context.user_data["selected_location_id"] = TEST_ADDRESS_ID
    context.user_data["final_address_name"] = TEST_ADDRESS_NAME
    context.facade.subscribe_address_for_user.return_value = True

    from telegram.ext import ConversationHandler
    state = await set_notification_time(update, context)

    assert state == ConversationHandler.END
    context.facade.subscribe_address_for_user.assert_called_once_with(
        chat_id=CHAT_ID,
        address_id=TEST_ADDRESS_ID,
        address_name=TEST_ADDRESS_NAME,
        notification_time="evening"
    )
    assert "erfolgreich eingerichtet" in update.message.reply_text.call_args_list[-1][0][0]
    assert len(context.user_data) == 0  # cleared
