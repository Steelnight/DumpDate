"""
Unit tests for the SmartScheduleService.
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from schedule_parser.models import WasteEvent
from schedule_parser.services.smart_schedule_service import \
    SmartScheduleService


class MockDate(date):
    """A mock date class to override today() within the class under test."""

    @classmethod
    def today(cls):
        return cls._today


@pytest.fixture
def mock_persistence_service():
    """Fixture for mocking the PersistenceService."""
    mock = MagicMock()
    # Mock context manager behavior
    mock.__enter__.return_value = mock
    mock.__exit__.return_value = None
    return mock


@pytest.fixture
def mock_schedule_service():
    """Fixture for mocking the ScheduleService."""
    return MagicMock()


class TestSmartScheduleService:
    """Tests for the SmartScheduleService class."""

    def setup_method(self):
        """Setup method called before each test."""
        self.persistence_service = MagicMock()
        self.schedule_service = MagicMock()
        # Mock context manager for persistence service
        self.persistence_service.__enter__.return_value = self.persistence_service
        self.persistence_service.__exit__.return_value = None

        self.service = SmartScheduleService(
            self.persistence_service, self.schedule_service
        )

    @patch("schedule_parser.services.smart_schedule_service.date", MockDate)
    def test_update_all_schedules_with_locations(self):
        """
        Test the successful update of schedules for subscribed locations.
        """
        MockDate.today = classmethod(lambda cls: date(2024, 1, 1))

        locations = [
            {"address_id": 1, "address": "Address 1"},
            {"address_id": 2, "address": "Address 2"},
        ]
        events = [
            WasteEvent(
                uid="1",
                date=(date(2024, 1, 2)).isoformat(),
                location="Location 1",
                waste_type="Bio-Tonne",
                contact_name="Contact",
                contact_phone="12345",
                original_address="Address 1",
                address_id=1
            )
        ]

        self.persistence_service.get_unique_subscribed_locations.return_value = (
            locations
        )
        self.schedule_service.download_and_parse_schedule.return_value = events

        self.service.update_all_schedules()

        # Check if locations were fetched
        self.persistence_service.get_unique_subscribed_locations.assert_called_once()
        # Check if download was called for each location (2 times)
        assert self.schedule_service.download_and_parse_schedule.call_count == 2
        # Check if upsert was called
        self.persistence_service.upsert_event.assert_called()

    @patch("schedule_parser.services.smart_schedule_service.date", MockDate)
    def test_update_all_schedules_filters_holidays_and_past_dates(self):
        """
        Test that the service correctly filters out holidays and past dates.
        """
        today = date(2023, 12, 31)
        MockDate.today = classmethod(lambda cls: today)

        locations = [{"address_id": 1, "address": "Test Address"}]
        self.persistence_service.get_unique_subscribed_locations.return_value = (
            locations
        )

        events = [
            WasteEvent(
                uid="past",
                date=(today - timedelta(days=1)).isoformat(),
                location="L",
                waste_type="W",
                contact_name="C",
                contact_phone="P",
                original_address="A",
                address_id=1
            ),
            WasteEvent(
                uid="holiday",
                date=date(2024, 1, 1).isoformat(),
                location="L",
                waste_type="W",
                contact_name="C",
                contact_phone="P",
                original_address="A",
                address_id=1
            ),  # New Year's Day
            WasteEvent(
                uid="valid",
                date=(today + timedelta(days=2)).isoformat(),
                location="L",
                waste_type="W",
                contact_name="C",
                contact_phone="P",
                original_address="A",
                address_id=1
            ),
        ]

        self.schedule_service.download_and_parse_schedule.return_value = events

        self.service.update_all_schedules()

        # Should only upsert the valid event
        # (past is filtered by code? No, past events are usually kept if recent, but let's see implementation)
        # Wait, SmartScheduleService calls _filter_and_store_events.
        # Let's check logic: if event.date < today -> skip. if holiday -> skip.
        # "past" event date is yesterday -> skip.
        # "holiday" event date is Jan 1st -> skip (New Year).
        # "valid" event date is Jan 2nd -> keep.

        # So only 1 upsert expected.
        assert self.persistence_service.upsert_event.call_count == 1
        args, _ = self.persistence_service.upsert_event.call_args
        assert args[0].uid == "valid"

    def test_update_all_schedules_no_subscriptions(self):
        """
        Test that nothing happens if there are no subscribed locations.
        """
        self.persistence_service.get_unique_subscribed_locations.return_value = []

        self.service.update_all_schedules()

        self.schedule_service.download_and_parse_schedule.assert_not_called()
