"""
This script runs the smart scheduler to periodically update waste schedules.
"""
import asyncio
import logging
from schedule_parser.config import LOG_LEVEL, SCHEDULE_UPDATE_INTERVAL_HOURS
from schedule_parser.services.persistence_service import PersistenceService
from schedule_parser.services.schedule_service import ScheduleService
from schedule_parser.services.smart_schedule_service import SmartScheduleService

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_scheduler() -> None:
    """
    Initializes services and runs the schedule update loop.
    """
    persistence_service = PersistenceService()
    schedule_service = ScheduleService()
    smart_schedule_service = SmartScheduleService(
        persistence_service=persistence_service, schedule_service=schedule_service
    )

    while True:
        try:
            logger.info("Running smart schedule update...")
            smart_schedule_service.update_all_schedules()
            logger.info("Smart schedule update finished.")
        except Exception as e:
            logger.exception(f"An error occurred during the smart schedule update: {e}")

        sleep_duration = SCHEDULE_UPDATE_INTERVAL_HOURS * 3600
        logger.info(f"Sleeping for {SCHEDULE_UPDATE_INTERVAL_HOURS} hours...")
        await asyncio.sleep(sleep_duration)


if __name__ == "__main__":
    logger.info("Starting the smart scheduler...")
    asyncio.run(run_scheduler())
