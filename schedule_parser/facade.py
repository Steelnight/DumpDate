"""
This module defines the central facade for the waste management application.
"""

import logging
from datetime import date
from typing import List, Optional

from .exceptions import DownloadError, ParsingError
from .services.notification_service import NotificationService
from .services.persistence_service import PersistenceService
from .services.schedule_service import ScheduleService
from .services.smart_schedule_service import SmartScheduleService
from .services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)


class WasteManagementFacade:
    """
    The central entry point for the waste management application.
    It orchestrates the various services to perform high-level operations.
    """

    def __init__(
        self,
        schedule_service: ScheduleService,
        persistence_service: PersistenceService,
        subscription_service: SubscriptionService,
        notification_service: NotificationService,
        smart_schedule_service: SmartScheduleService,
    ):
        self.schedule_service = schedule_service
        self.persistence_service = persistence_service
        self.subscription_service = subscription_service
        self.notification_service = notification_service
        self.smart_schedule_service = smart_schedule_service

    def subscribe_address_for_user(
        self, chat_id: int, address_id: int, address_name: str, notification_time: str
    ) -> bool:
        """
        Subscribes a user to a given address ID.

        This method handles the full workflow:
        1. Downloads the schedule (if not already cached or to verify).
        2. Stores the schedule events.
        3. Creates or updates the subscription with the custom name.

        Args:
            chat_id: The user's chat ID.
            address_id: The location ID (STANDORT).
            address_name: The name the user wants to give to this address.
            notification_time: The preferred notification time ('morning' or 'evening').

        Returns:
            True if the subscription was successful, False otherwise.

        Raises:
            DownloadError: If the schedule download fails.
            ParsingError: If the schedule parsing fails.
        """
        try:
            logger.info(
                f"Starting subscription for chat_id {chat_id}, ID {address_id}, Name '{address_name}'."
            )

            # 1. Download and parse schedule
            today = date.today()
            end_of_year = date(today.year, 12, 31)

            # We pass the address_name as original_address so events are tagged with it.
            # Note: If multiple users use different names for the same ID,
            # the last one might overwrite the 'original_address' field in events.
            # This is acceptable as long as we can still find events.
            events = self.schedule_service.download_and_parse_schedule(
                standort_id=address_id,
                start_date=today,
                end_date=end_of_year,
                original_address=address_name,
            )

            # 2. Store events
            with self.persistence_service as p:
                for event in events:
                    p.upsert_event(event)

            # 3. Create or update subscription
            self.subscription_service.add_or_reactivate_subscription(
                chat_id=chat_id,
                address_id=address_id,
                address_name=address_name,
                notification_time=notification_time,
            )

            logger.info(
                f"Successfully subscribed chat_id {chat_id} to ID {address_id} ('{address_name}')."
            )
            return True

        except (ValueError, DownloadError, ParsingError) as e:
            # Expected errors that the caller (bot) can handle
            logger.warning(
                f"A specific error occurred during subscription for chat_id {chat_id}: {e}"
            )
            raise
        except Exception as e:
            # Unexpected errors
            logger.exception(
                f"An unexpected error occurred during subscription for chat_id {chat_id} and ID {address_id}: {e}"
            )
            return False

    def verify_location_id(self, location_id: int) -> Optional[str]:
        """
        Verifies if a location ID is valid and returns the address name found in the schedule.
        """
        return self.schedule_service.get_address_from_id(location_id)

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
            logger.exception(
                f"Failed to unsubscribe subscription_id {subscription_id}: {e}"
            )
            return False

    def get_address_by_id(self, address_id: int) -> Optional[str]:
        """Gets an address string by its ID."""
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

    # --- Notification Cycle Methods ---

    def get_due_notifications(self) -> List[dict]:
        """Gets all notifications that are due to be sent."""
        try:
            return self.notification_service.get_due_notifications()
        except Exception:
            logger.exception("Failed to get due notifications.")
            return []

    def log_pending_notification(self, subscription_id: int) -> Optional[int]:
        """Logs that a notification is about to be sent."""
        try:
            return self.notification_service.log_pending_notification(subscription_id)
        except Exception:
            logger.exception(
                f"Failed to log pending notification for sub_id {subscription_id}."
            )
            return None

    def update_notification_log(
        self, log_id: int, status: str, error_message: Optional[str] = None
    ) -> None:
        """Updates the status of a sent notification."""
        try:
            self.notification_service.update_notification_log(
                log_id, status, error_message
            )
        except Exception:
            logger.exception(f"Failed to update notification log for log_id {log_id}.")

    def update_last_notified_date(
        self, subscription_id: int, collection_date: date
    ) -> None:
        """Updates the last notified date for a subscription."""
        try:
            self.subscription_service.update_last_notified(
                subscription_id, collection_date.isoformat()
            )
        except Exception:
            logger.exception(
                f"Failed to update last notified date for sub_id {subscription_id}."
            )

    def get_next_pickup_for_user(self, chat_id: int) -> List[dict]:
        """Gets the next pickup for each of a user's subscriptions."""
        subscriptions = self.get_user_subscriptions(chat_id)
        if not subscriptions:
            return []

        today = date.today().isoformat()
        next_pickups = []

        with self.persistence_service as p:
            for sub in subscriptions:
                event = p.get_next_waste_event_for_subscription(
                    sub["address_id"], today
                )
                if event:
                    # Use the name the user gave, or fallback to something else
                    address = sub["address_name"] or self.get_address_by_id(sub["address_id"])
                    next_pickups.append({"address": address, "event": event})
        return next_pickups
