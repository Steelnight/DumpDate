import pytest
from datetime import date
from unittest.mock import patch

from schedule_parser.facade import get_schedule_for_address
from schedule_parser.models import WasteEvent


@pytest.fixture
def mock_address_service():
    """Mocks the AddressService."""
    with patch("schedule_parser.facade.AddressService") as mock_service_class:
        mock_instance = mock_service_class.return_value
        mock_instance.get_id_for_address.return_value = 54321
        yield mock_instance


@pytest.fixture
def mock_schedule_service():
    """Mocks the ScheduleService."""
    with patch("schedule_parser.facade.ScheduleService") as mock_service_class:
        mock_instance = mock_service_class.return_value
        mock_instance.get_schedule.return_value = [
            WasteEvent(
                uid="1",
                date="2026-01-01",
                location="Test",
                waste_type="Restmüll",
                contact_name="",
                contact_phone="",
                original_address="Chemnitzer Straße 42",
            )
        ]
        yield mock_instance


@pytest.fixture
def mock_persistence_service():
    """Mocks the PersistenceService."""
    with patch("schedule_parser.facade.PersistenceService") as mock_service_class:
        mock_instance = mock_service_class.return_value
        yield mock_instance


def test_get_schedule_for_address_orchestration(
    tmp_path,
    mock_address_service,
    mock_schedule_service,
    mock_persistence_service,
):
    """
    Tests that the facade correctly orchestrates the service calls.
    """
    db_path = str(tmp_path / "test_waste.db")
    address = "Chemnitzer Straße 42"
    start_date = date(2026, 1, 1)
    end_date = date(2026, 12, 31)

    # Call the main facade function
    get_schedule_for_address(
        address=address,
        start_date=start_date,
        end_date=end_date,
        db_path=db_path,
    )

    # Verify AddressService was called correctly
    mock_address_service.get_id_for_address.assert_called_once_with(address)

    # Verify ScheduleService was called correctly
    mock_schedule_service.get_schedule.assert_called_once_with(
        54321, start_date, end_date, original_address=address
    )

    # Verify PersistenceService was initialized and used correctly
    mock_persistence_service.save_events.assert_called_once()
    assert (
        mock_persistence_service.save_events.call_args[0][0]
        == mock_schedule_service.get_schedule.return_value
    )
