"""
This module defines the NotificationService for handling notifications.
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from .persistence_service import PersistenceService


class NotificationService:
    """Handles the business logic for creating and sending notifications."""

    def __init__(self, persistence_service: PersistenceService):
        self.persistence = persistence_service

    def get_due_notifications(self) -> List[Dict[str, Any]]:
        """
        Gathers all notifications that are due to be sent.

        Returns:
            A list of dictionaries, where each dictionary represents a notification task.
        """
        with self.persistence as p:
            subscriptions = p.get_all_active_subscriptions()
            all_events = p.get_all_waste_events()  # Assuming this method exists

        events_by_address = {}
        for event in all_events:
            address = event["original_address"]
            if address not in events_by_address:
                events_by_address[address] = []
            events_by_address[address].append(event)

        notification_tasks = []
        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)

        for sub in subscriptions:
            address = self._get_address_for_subscription(
                sub
            )  # Helper to get address string
            if not address:
                continue

            collections = events_by_address.get(address, [])
            last_notified = (
                date.fromisoformat(sub["last_notified"])
                if sub["last_notified"]
                else None
            )

            for collection in collections:
                collection_date = date.fromisoformat(collection["date"])
                waste_type = collection["waste_type"]

                if last_notified == collection_date:
                    continue

                message = None
                notification_time = sub["notification_time"]

                # Evening before notification
                if (
                    notification_time == "evening"
                    and collection_date == tomorrow
                    and now.hour >= 19
                ):
                    emoji = self._get_waste_type_emoji(waste_type)
                    message = f"{emoji} {waste_type} ist für morgen geplant!"

                # Morning of notification
                elif (
                    notification_time == "morning"
                    and collection_date == today
                    and now.hour >= 6
                ):
                    emoji = self._get_waste_type_emoji(waste_type)
                    message = f"{emoji} {waste_type} wird heute abgeholt!"

                if message:
                    notification_tasks.append(
                        {
                            "subscription_id": sub["id"],
                            "chat_id": sub["chat_id"],
                            "message": message,
                            "collection_date": collection_date,
                        }
                    )
        return notification_tasks

    def _get_address_for_subscription(self, subscription: Dict[str, Any]) -> str:
        """Helper to get the address string for a subscription."""
        # This is a placeholder. The actual implementation will depend on how
        # addresses are stored and related to subscriptions.
        with self.persistence as p:
            # Assuming a method to get address string by its ID
            return p.get_address_by_id(subscription["address_id"])

    def _get_waste_type_emoji(self, waste_type: str) -> str:
        """Returns an emoji for a given waste type."""
        if "bio" in waste_type.lower():
            return "🟢"
        if "papier" in waste_type.lower():
            return "🔵"
        if "gelbe" in waste_type.lower() or "verpackung" in waste_type.lower():
            return "🟡"
        if "rest" in waste_type.lower():
            return "⚫"
        return "🗑️"

    def log_pending_notification(self, subscription_id: int) -> int:
        """Logs a pending notification and returns the log ID."""
        with self.persistence as p:
            return p.create_notification_log(subscription_id, "pending")

    def update_notification_log(
        self, log_id: int, status: str, error_message: str = None
    ) -> None:
        """Updates the status of a notification log."""
        with self.persistence as p:
            p.update_notification_log_status(log_id, status, error_message)
