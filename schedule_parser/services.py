"""
This module provides a service layer for the schedule_parser application.

It encapsulates the core logic of the application into distinct services,
each with a specific responsibility. This approach improves modularity,
makes the code easier to test, and clarifies dependencies.
"""
import os
import logging
from datetime import date
from typing import List

from .models import WasteEvent
from .address_cache import get_address_id
from .ical_downloader import download_ical_file
from .ics_parser import parse_ics
from .db_manager import init_db, upsert_event
from .config import ADDRESS_DB_FILE, SCHEDULE_DB_FILE

logger = logging.getLogger(__name__)


class AddressService:
    """A service for handling address-related operations."""

    def __init__(self, db_path: str = ADDRESS_DB_FILE):
        self._db_path = db_path

    def get_id_for_address(self, address: str) -> int:
        """
        Retrieves the unique ID for a given address from the cache.

        Args:
            address: The street address to look up.

        Returns:
            The corresponding address ID.

        Raises:
            ValueError: If the address is not found in the cache.
            FileNotFoundError: If the address cache database does not exist.
        """
        return get_address_id(address, db_path=self._db_path)


class ScheduleService:
    """A service for downloading and parsing waste schedules."""

    def get_schedule(
        self, address_id: int, start_date: date, end_date: date, original_address: str
    ) -> List[WasteEvent]:
        """
        Downloads and parses the waste schedule for a given address ID.

        Args:
            address_id: The ID of the address.
            start_date: The start date for the schedule.
            end_date: The end date for the schedule.
            original_address: The original address string to store with the events.

        Returns:
            A list of WasteEvent objects.
        """
        ical_file_path = download_ical_file(address_id, start_date, end_date)
        if ical_file_path is None:
            logger.error(
                f"Could not download iCal file for address ID {address_id}. Aborting."
            )
            return []

        try:
            with open(ical_file_path, "r", encoding="utf-8") as f:
                ics_text = f.read()

            waste_events = parse_ics(ics_text, original_address)
            logger.info(f"Parsed {len(waste_events)} events from the iCal file.")
            return waste_events
        finally:
            if os.path.exists(ical_file_path):
                os.remove(ical_file_path)
                logger.info(f"Removed temporary file: {ical_file_path}")
        return []


class PersistenceService:
    """A service for saving waste schedule data to the database."""

    def __init__(self, db_path: str = SCHEDULE_DB_FILE):
        self._db_path = db_path
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Initializes the database schema if it doesn't exist."""
        init_db(self._db_path)

    def save_events(self, events: List[WasteEvent]) -> None:
        """
        Saves a list of waste events to the database.

        Args:
            events: A list of WasteEvent objects to save.
        """
        for event in events:
            upsert_event(event, self._db_path)
        logger.info(
            f"Successfully stored {len(events)} events in the database at {self._db_path}."
        )
