"""
Unit tests for the WasteManagementFacade.
"""

from unittest.mock import MagicMock

import pytest

from schedule_parser.exceptions import DownloadError
from schedule_parser.facade import WasteManagementFacade
from schedule_parser.models import WasteEvent


# A fixture to create a set of mocked services for each test
@pytest.fixture
def mock_services():
    return {
        # AddressService is removed
        "schedule_service": MagicMock(),
        "persistence_service": MagicMock(),
        "subscription_service": MagicMock(),
        "notification_service": MagicMock(),
        "smart_schedule_service": MagicMock(),
    }


def test_subscribe_address_for_user_success(mock_services):
    """
    Tests the successful workflow of subscribing a user to an address.
    """
    # Arrange
    facade = WasteManagementFacade(**mock_services)
    mock_schedule_service = mock_services["schedule_service"]
    mock_persistence_service = mock_services["persistence_service"]
    mock_subscription_service = mock_services["subscription_service"]

    mock_schedule_service.download_and_parse_schedule.return_value = [
        WasteEvent("uid1", "2023-10-27", "loc", "Rest", "", "", "addr", 123)
    ]

    # Use the persistence service as a context manager
    mock_persistence_instance = mock_persistence_service.__enter__.return_value

    # Act
    result = facade.subscribe_address_for_user(
        chat_id=999, address_id=123, address_name="Home", notification_time="evening"
    )

    # Assert
    assert result is True
    mock_schedule_service.download_and_parse_schedule.assert_called_once()
    mock_persistence_instance.upsert_event.assert_called_once()
    mock_subscription_service.add_or_reactivate_subscription.assert_called_once_with(
        chat_id=999, address_id=123, address_name="Home", notification_time="evening"
    )

def test_subscribe_unexpected_error_is_handled_gracefully(mock_services):
    """
    Tests that an unexpected exception from a service is caught and handled.
    (False-Positive / Unexpected Failure Test)
    """
    # Arrange
    facade = WasteManagementFacade(**mock_services)
    mock_persistence_service = mock_services["persistence_service"]
    # Simulate a generic, unexpected error during the DB save
    mock_persistence_service.__enter__.side_effect = Exception(
        "Database connection failed"
    )

    # Act
    result = facade.subscribe_address_for_user(
        chat_id=999, address_id=123, address_name="Home", notification_time="evening"
    )

    # Assert
    assert result is False
    # Ensure add_or_reactivate_subscription was not called
    mock_services[
        "subscription_service"
    ].add_or_reactivate_subscription.assert_not_called()


def test_subscribe_download_error_is_raised(mock_services):
    """
    Tests that a DownloadError from the ScheduleService is propagated correctly.
    """
    # Arrange
    facade = WasteManagementFacade(**mock_services)
    mock_schedule_service = mock_services["schedule_service"]
    mock_schedule_service.download_and_parse_schedule.side_effect = DownloadError(
        "Network timeout"
    )

    # Act & Assert
    with pytest.raises(DownloadError, match="Network timeout"):
        facade.subscribe_address_for_user(
            chat_id=999, address_id=123, address_name="Home", notification_time="evening"
        )
