"""
This module provides a facade for the schedule_parser library.

It orchestrates the process of fetching, parsing, and storing waste schedules.
"""
import logging
import os
from datetime import date

from .address_finder import get_address_id
from .db_manager import init_db, upsert_event
from .ical_downloader import download_ical_file
from .ics_parser import parse_ics

# Get a logger instance for this module
logger = logging.getLogger(__name__)


def get_schedule_for_address(
    address: str, start_date: date, end_date: date, db_path: str = "waste_schedule.db"
) -> None:
    """
    Orchestrates the process of fetching, parsing, and storing waste schedules.

    Args:
        address: The address to get the schedule for.
        start_date: The start date for the schedule.
        end_date: The end date for the schedule.
        db_path: The path to the SQLite database.
    """
    try:
        # 1. Get address ID
        address_id = get_address_id(address)

        # 2. Download iCal file
        ical_file_path = download_ical_file(address_id, start_date, end_date)
        if ical_file_path is None:
            logger.error(
                f"Could not download iCal file for address ID {address_id}. Aborting."
            )
            return

        # 3. Parse the iCal file
        try:
            with open(ical_file_path, "r", encoding="utf-8") as f:
                ics_text = f.read()

            waste_events = parse_ics(ics_text)
            logger.info(f"Parsed {len(waste_events)} events from the iCal file.")

            # 4. Initialize DB and store events
            init_db(db_path)
            for event in waste_events:
                upsert_event(event, db_path)
            logger.info(
                f"Successfully stored {len(waste_events)} events in the database at {db_path}."
            )

        finally:
            # 5. Clean up the temporary file
            if os.path.exists(ical_file_path):
                os.remove(ical_file_path)
                logger.info(f"Removed temporary file: {ical_file_path}")

    except ValueError as e:
        logger.error(e)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
