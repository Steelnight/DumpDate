"""
This module defines the SmartScheduleService for intelligently updating waste schedules.
"""

import asyncio
import logging
from datetime import date, timedelta

import holidays

from schedule_parser.config import SCHEDULE_UPDATE_INTERVAL_HOURS

from ..exceptions import DownloadError, ParsingError
from .persistence_service import PersistenceService
from .schedule_service import ScheduleService

logger = logging.getLogger(__name__)


class SmartScheduleService:
    """
    Manages the intelligent downloading and updating of waste schedules.
    """

    def __init__(
        self,
        persistence_service: PersistenceService,
        schedule_service: ScheduleService,
        weeks_to_fetch: int = 6,
    ):
        self.persistence_service = persistence_service
        self.schedule_service = schedule_service
        self.weeks_to_fetch = weeks_to_fetch
        self.german_holidays = holidays.Germany(subdiv="SN")  # Saxony

    def update_all_schedules(self) -> None:
        """
        Orchestrates the update process for all unique subscribed locations.
        """
        logger.info("Starting smart schedule update for all subscribed locations.")
        unique_locations = self.persistence_service.get_unique_subscribed_locations()

        if not unique_locations:
            logger.info("No subscribed locations found. Skipping schedule update.")
            return

        start_date = date.today()
        end_date = start_date + timedelta(weeks=self.weeks_to_fetch)

        for location in unique_locations:
            standort_id = location["address_id"]
            original_address = location["address"]

            logger.info(
                f"Processing schedule for {original_address} (ID: {standort_id})."
            )

            try:
                new_events = self.schedule_service.download_and_parse_schedule(
                    standort_id, start_date, end_date, original_address
                )

                if not new_events:
                    logger.warning(
                        f"No events found for {original_address}. It might be a holiday period or an issue with the source."
                    )
                    continue

                # Filter out holidays and past dates
                valid_events = [
                    event
                    for event in new_events
                    if date.fromisoformat(event.date) >= start_date
                    and date.fromisoformat(event.date) not in self.german_holidays
                ]

                with self.persistence_service as db:
                    for event in valid_events:
                        db.upsert_event(event)

                logger.info(f"Successfully updated schedule for {original_address}.")

            except (DownloadError, ParsingError) as e:
                logger.error(
                    f"Failed to update schedule for {original_address} (ID: {standort_id}): {e}"
                )
            except Exception as e:
                logger.exception(
                    f"An unexpected error occurred while updating schedule for {original_address} (ID: {standort_id}): {e}"
                )

        logger.info("Smart schedule update completed.")

    async def run_scheduler(self) -> None:
        """
        Runs the schedule update loop indefinitely.
        """
        while True:
            try:
                logger.info("Running smart schedule update...")
                self.update_all_schedules()
                logger.info("Smart schedule update finished.")
            except Exception as e:
                logger.exception(
                    f"An error occurred during the smart schedule update: {e}"
                )

            sleep_duration = SCHEDULE_UPDATE_INTERVAL_HOURS * 3600
            logger.info(f"Sleeping for {SCHEDULE_UPDATE_INTERVAL_HOURS} hours...")
            await asyncio.sleep(sleep_duration)
