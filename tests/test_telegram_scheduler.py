"""
Tests for the Telegram bot's scheduler.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from telegram_bot.scheduler import check_and_send_notifications


@pytest.fixture
def mock_facade():
    """Returns a mock WasteManagementFacade."""
    facade = MagicMock()
    facade.get_due_notifications.return_value = []
    facade.log_pending_notification.return_value = 1
    facade.update_notification_log = MagicMock()
    facade.update_last_notified_date = MagicMock()
    return facade


@pytest.fixture
def mock_bot():
    """Returns a mock Telegram bot."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    return bot


@pytest.mark.asyncio
async def test_check_and_send_notifications_no_notifications(mock_facade, mock_bot):
    """
    Tests that no notifications are sent when there are no due notifications.
    """
    await check_and_send_notifications(mock_facade, mock_bot)
    mock_facade.get_due_notifications.assert_called_once()
    mock_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_check_and_send_notifications_sends_successfully(mock_facade, mock_bot):
    """
    Tests that notifications are sent successfully when there are due notifications.
    """
    notifications = [
        {
            "subscription_id": 1,
            "chat_id": 123,
            "message": "Test message 1",
            "collection_date": "2025-10-24",
        },
        {
            "subscription_id": 2,
            "chat_id": 456,
            "message": "Test message 2",
            "collection_date": "2025-10-25",
        },
    ]
    mock_facade.get_due_notifications.return_value = notifications

    await check_and_send_notifications(mock_facade, mock_bot)

    assert mock_facade.get_due_notifications.call_count == 1
    assert mock_bot.send_message.call_count == 2
    mock_facade.update_notification_log.assert_called()


@pytest.mark.asyncio
async def test_check_and_send_notifications_handles_failure(mock_facade, mock_bot):
    """
    Tests that the scheduler handles failures when sending notifications.
    """
    notifications = [
        {
            "subscription_id": 1,
            "chat_id": 123,
            "message": "Test message 1",
            "collection_date": "2025-10-24",
        },
    ]
    mock_facade.get_due_notifications.return_value = notifications
    mock_bot.send_message.side_effect = Exception("Test error")

    await check_and_send_notifications(mock_facade, mock_bot)

    assert mock_facade.get_due_notifications.call_count == 1
    assert mock_bot.send_message.call_count == 1
    mock_facade.update_notification_log.assert_called_with(1, "failure", "Test error")
