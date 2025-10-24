"""
This module defines the central facade for the waste management application.
"""
import logging
from datetime import date, timedelta
from typing import List, Optional

from .services.address_service import AddressService
from .services.notification_service import NotificationService
from .services.persistence_service import PersistenceService
from .services.schedule_service import ScheduleService
from .services.subscription_service import SubscriptionService
from .exceptions import DownloadError, ParsingError
from .models import WasteEvent

logger = logging.getLogger(__name__)


class WasteManagementFacade:
    """
    The central entry point for the waste management application.
    It orchestrates the various services to perform high-level operations.
    """

    def __init__(
        self,
        address_service: AddressService,
        schedule_service: ScheduleService,
        persistence_service: PersistenceService,
        subscription_service: SubscriptionService,
        notification_service: NotificationService,
    ):
        self.address_service = address_service
        self.schedule_service = schedule_service
        self.persistence_service = persistence_service
        self.subscription_service = subscription_service
        self.notification_service = notification_service

    def subscribe_address_for_user(
        self, chat_id: int, address: str, notification_time: str
    ) -> bool:
        """
        Subscribes a user to a given address.

        This method handles the full workflow:
        1. Finds the address ID.
        2. Downloads the schedule.
        3. Stores the schedule events.
        4. Creates or updates the subscription.

        Args:
            chat_id: The user's chat ID.
            address: The address to subscribe to.
            notification_time: The preferred notification time ('morning' or 'evening').

        Returns:
            True if the subscription was successful, False otherwise.

        Raises:
            ValueError: If the address is not found.
            FileNotFoundError: If the address database is missing.
            DownloadError: If the schedule download fails.
            ParsingError: If the schedule parsing fails.
        """
        try:
            logger.info(f"Starting subscription for chat_id {chat_id} and address '{address}'.")

            # 1. Find address ID
            address_id = self.address_service.get_address_id(address)

            # 2. Download and parse schedule
            today = date.today()
            end_of_year = date(today.year, 12, 31)
            events = self.schedule_service.download_and_parse_schedule(
                standort_id=address_id,
                start_date=today,
                end_date=end_of_year,
                original_address=address,
            )

            # 3. Store events
            with self.persistence_service as p:
                for event in events:
                    p.upsert_event(event)

            # 4. Create or update subscription
            self.subscription_service.add_or_reactivate_subscription(
                chat_id=chat_id,
                address_id=address_id,
                notification_time=notification_time,
            )

            logger.info(f"Successfully subscribed chat_id {chat_id} to address '{address}'.")
            return True

        except (ValueError, FileNotFoundError, DownloadError, ParsingError) as e:
            # Expected errors that the caller (bot) can handle
            logger.warning(f"A specific error occurred during subscription for chat_id {chat_id}: {e}")
            raise
        except Exception as e:
            # Unexpected errors
            logger.exception(
                f"An unexpected error occurred during subscription for chat_id {chat_id} and address '{address}': {e}"
            )
            return False

    def get_user_subscriptions(self, chat_id: int) -> List[dict]:
        """Retrieves a user's active subscriptions."""
        try:
            return self.subscription_service.get_user_subscriptions(chat_id)
        except Exception as e:
            logger.exception(f"Failed to get subscriptions for chat_id {chat_id}: {e}")
            return []

    def unsubscribe(self, subscription_id: int) -> bool:
        """Unsubscribes a user from a specific subscription."""
        try:
            self.subscription_service.remove_subscription(subscription_id)
            logger.info(f"Successfully unsubscribed subscription_id {subscription_id}.")
            return True
        except Exception as e:
            logger.exception(f"Failed to unsubscribe subscription_id {subscription_id}: {e}")
            return False

    def find_address_matches(self, query: str) -> List[tuple[str, int]]:
        """Finds potential address matches for a given query."""
        try:
            return self.address_service.find_address_matches(query)
        except FileNotFoundError:
            # This is an expected error if the cache hasn't been built
            raise
        except Exception as e:
            logger.exception(f"An unexpected error occurred while finding address matches for query '{query}': {e}")
            return []

    def get_address_by_id(self, address_id: int) -> Optional[str]:
        """Gets an address string by its ID."""
        # This is a bit of a workaround, as the address string is not stored in the main DB.
        # Ideally, the subscriptions table would store the address string directly.
        try:
            with self.persistence_service as p:
                return p.get_address_by_id(address_id)
        except Exception as e:
            logger.exception(f"Failed to get address for address_id {address_id}: {e}")
            return None

    def get_dashboard_data(self) -> dict:
        """Retrieves all necessary data for the dashboard."""
        try:
            with self.persistence_service as p:
                events = p.get_all_waste_events()
                subscriptions = p.get_all_active_subscriptions()
                logs = p.get_all_logs()
            return {
                "events": events,
                "subscriptions": subscriptions,
                "logs": logs,
            }
        except Exception as e:
            logger.exception("Failed to retrieve dashboard data.")
            return {
                "events": [],
                "subscriptions": [],
                "logs": [],
                "error": str(e),
            }
