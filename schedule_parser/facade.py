"""
This module provides a facade for the schedule_parser library.

It orchestrates the process of fetching, parsing, and storing waste schedules.
"""
import logging
from datetime import date

from .services import AddressService, ScheduleService, PersistenceService
from .config import SCHEDULE_DB_FILE

# Get a logger instance for this module
logger = logging.getLogger(__name__)


def get_schedule_for_address(
    address: str,
    start_date: date,
    end_date: date,
    db_path: str = SCHEDULE_DB_FILE,
) -> None:
    """
    Orchestrates the process of fetching, parsing, and storing waste schedules.

    This function uses a service-oriented architecture to separate concerns:
    - AddressService: To look up the address ID.
    - ScheduleService: To download and parse the schedule.
    - PersistenceService: To save the schedule to a database.

    Args:
        address: The address to get the schedule for.
        start_date: The start date for the schedule.
        end_date: The end date for the schedule.
        db_path: The path to the SQLite database.
    """
    try:
        # Initialize services
        address_service = AddressService()
        schedule_service = ScheduleService()
        persistence_service = PersistenceService(db_path=db_path)

        # 1. Get address ID
        logger.info(f"Attempting to find address ID for '{address}'...")
        address_id = address_service.get_id_for_address(address)
        logger.info(f"Found address ID: {address_id}")

        # 2. Download and parse the schedule
        logger.info(f"Fetching schedule for address ID {address_id}...")
        waste_events = schedule_service.get_schedule(
            address_id, start_date, end_date, original_address=address
        )

        # 3. Save the events to the database
        if waste_events:
            logger.info(f"Saving {len(waste_events)} events to the database...")
            persistence_service.save_events(waste_events)
        else:
            logger.warning(f"No schedule events found for '{address}'.")

    except (ValueError, FileNotFoundError) as e:
        # Log known, expected errors (e.g., address not found)
        logger.error(f"A handled error occurred: {e}")
    except Exception as e:
        # Log any other unexpected errors
        logger.error(f"An unexpected error occurred during the process: {e}", exc_info=True)
