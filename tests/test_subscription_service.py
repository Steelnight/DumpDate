"""
Unit tests for the SubscriptionService.
"""

from unittest.mock import MagicMock

from schedule_parser.services.subscription_service import SubscriptionService


def test_add_or_reactivate_subscription_new():
    """Tests adding a completely new subscription."""
    mock_persistence = MagicMock()
    mock_persistence.__enter__.return_value.find_subscription_by_chat_and_address.return_value = (
        None
    )
    service = SubscriptionService(persistence_service=mock_persistence)

    service.add_or_reactivate_subscription(1, 10, "Home", "evening")

    mock_persistence.__enter__.return_value.create_subscription.assert_called_once_with(
        1, 10, "Home", "evening"
    )
    mock_persistence.__enter__.return_value.reactivate_subscription.assert_not_called()


def test_add_or_reactivate_subscription_existing():
    """Tests reactivating an existing subscription."""
    mock_persistence = MagicMock()
    mock_persistence.__enter__.return_value.find_subscription_by_chat_and_address.return_value = {
        "id": 99
    }
    service = SubscriptionService(persistence_service=mock_persistence)

    service.add_or_reactivate_subscription(1, 10, "Home", "morning")

    mock_persistence.__enter__.return_value.create_subscription.assert_not_called()
    mock_persistence.__enter__.return_value.reactivate_subscription.assert_called_once_with(
        99, "Home", "morning"
    )
