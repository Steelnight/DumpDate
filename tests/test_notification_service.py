"""
Unit tests for the NotificationService.
"""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

from schedule_parser.services.notification_service import NotificationService

# Sample data to be returned by the mocked persistence service
SAMPLE_SUBSCRIPTIONS = [
    {
        "id": 1,
        "chat_id": 101,
        "address_id": 1,
        "notification_time": "evening",
        "last_notified": None,
    },
    {
        "id": 2,
        "chat_id": 102,
        "address_id": 2,
        "notification_time": "morning",
        "last_notified": "2023-10-26",
    },
]

SAMPLE_EVENTS = [
    {
        "original_address": "Test Straße 1",
        "date": "2023-10-27",
        "waste_type": "Rest-Tonne",
    },  # Tomorrow
    {
        "original_address": "Musterweg 2",
        "date": "2023-10-26",
        "waste_type": "Bio-Tonne",
    },  # Today
]


def test_get_due_notifications():
    """
    Tests the logic for identifying which notifications are due.
    """
    mock_persistence = MagicMock()
    mock_persistence_instance = mock_persistence.__enter__.return_value
    mock_persistence_instance.get_all_active_subscriptions.return_value = (
        SAMPLE_SUBSCRIPTIONS
    )
    mock_persistence_instance.get_all_waste_events.return_value = SAMPLE_EVENTS

    # Mock the address lookup
    def get_address_by_id_side_effect(address_id):
        if address_id == 1:
            return "Test Straße 1"
        if address_id == 2:
            return "Musterweg 2"
        return None

    mock_persistence_instance.get_address_by_id.side_effect = (
        get_address_by_id_side_effect
    )

    service = NotificationService(persistence_service=mock_persistence)

    # --- Simulate being in the evening of Oct 26th ---
    # We need to patch the datetime object *where it is used*
    with patch(
        "schedule_parser.services.notification_service.datetime"
    ) as mock_datetime:
        mock_datetime.now.return_value = datetime(2023, 10, 26, 19, 5)
        # To keep date consistent with datetime, we can derive it
        mock_datetime.today.return_value.date.return_value = date(2023, 10, 26)

        due_notifications = service.get_due_notifications()

    # Assertions
    # 1. The "evening" subscription for tomorrow's event should be due.
    # 2. The "morning" subscription for today's event should NOT be due (it's evening).
    # 3. The "morning" subscription should not be triggered for the already notified date.
    assert len(due_notifications) == 1
    notification = due_notifications[0]
    assert notification["subscription_id"] == 1
    assert "für morgen geplant" in notification["message"]
