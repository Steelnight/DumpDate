"""
Unit tests for the SmartScheduleService.
"""
import unittest
from unittest.mock import MagicMock, patch
from datetime import date, timedelta

from schedule_parser.services.smart_schedule_service import SmartScheduleService
from schedule_parser.models import WasteEvent

# A class to mock datetime.date, allowing 'today' to be controlled in tests.
class MockDate(date):
    @classmethod
    def today(cls):
        # Default value, can be overridden in each test.
        return date(2024, 1, 1)

class TestSmartScheduleService(unittest.IsolatedAsyncioTestCase):
    """Test suite for the SmartScheduleService."""

    def setUp(self):
        """Set up the test environment."""
        self.persistence_service = MagicMock()
        self.persistence_service.__enter__.return_value = self.persistence_service
        self.schedule_service = MagicMock()
        self.smart_schedule_service = SmartScheduleService(
            persistence_service=self.persistence_service,
            schedule_service=self.schedule_service,
        )

    @patch('schedule_parser.services.smart_schedule_service.date', MockDate)
    @patch('asyncio.sleep')
    async def test_update_all_schedules_no_locations(self, mock_sleep):
        """
        Test that the service handles the case where there are no subscribed locations.
        """
        self.persistence_service.get_unique_subscribed_locations.return_value = []
        await self.smart_schedule_service.update_all_schedules()
        self.schedule_service.download_and_parse_schedule.assert_not_called()

    @patch('schedule_parser.services.smart_schedule_service.date', MockDate)
    @patch('asyncio.sleep')
    async def test_update_all_schedules_with_locations(self, mock_sleep):
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
            )
        ]
        self.persistence_service.get_unique_subscribed_locations.return_value = locations
        self.schedule_service.download_and_parse_schedule.return_value = events

        await self.smart_schedule_service.update_all_schedules()

        self.assertEqual(self.schedule_service.download_and_parse_schedule.call_count, 2)
        self.assertEqual(self.persistence_service.upsert_event.call_count, 2)
        self.assertEqual(self.persistence_service.__enter__.call_count, 2)

    @patch('schedule_parser.services.smart_schedule_service.date', MockDate)
    @patch('asyncio.sleep')
    async def test_update_all_schedules_filters_holidays_and_past_dates(self, mock_sleep):
        """
        Test that the service correctly filters out holidays and past dates.
        """
        today = date(2023, 12, 31)
        MockDate.today = classmethod(lambda cls: today)

        locations = [{"address_id": 1, "address": "Test Address"}]
        self.persistence_service.get_unique_subscribed_locations.return_value = locations

        events = [
            WasteEvent(uid="past", date=(today - timedelta(days=1)).isoformat(), location="L", waste_type="W", contact_name="C", contact_phone="P", original_address="A"),
            WasteEvent(uid="holiday", date=date(2024, 1, 1).isoformat(), location="L", waste_type="W", contact_name="C", contact_phone="P", original_address="A"), # New Year's Day
            WasteEvent(uid="valid", date=(today + timedelta(days=2)).isoformat(), location="L", waste_type="W", contact_name="C", contact_phone="P", original_address="A"),
        ]

        self.schedule_service.download_and_parse_schedule.return_value = events

        await self.smart_schedule_service.update_all_schedules()

        self.schedule_service.download_and_parse_schedule.assert_called_once()
        self.persistence_service.__enter__.assert_called_once()
        self.persistence_service.upsert_event.assert_called_once()

        upserted_event = self.persistence_service.upsert_event.call_args[0][0]
        self.assertEqual(upserted_event.uid, "valid")

if __name__ == "__main__":
    unittest.main()
