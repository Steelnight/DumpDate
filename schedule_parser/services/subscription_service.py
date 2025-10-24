"""
This module defines the SubscriptionService for managing user subscriptions.
"""
from typing import List, Tuple

from .persistence_service import PersistenceService


class SubscriptionService:
    """Handles business logic for user subscriptions."""

    def __init__(self, persistence_service: PersistenceService):
        self.persistence = persistence_service

    def add_or_reactivate_subscription(
        self, chat_id: int, address_id: int, notification_time: str
    ) -> None:
        """Adds a new subscription or reactivates an existing one."""
        with self.persistence as p:
            existing_sub = p.find_subscription_by_chat_and_address(chat_id, address_id)
            if existing_sub:
                p.reactivate_subscription(existing_sub["id"], notification_time)
            else:
                p.create_subscription(chat_id, address_id, notification_time)

    def get_user_subscriptions(self, chat_id: int) -> List[dict]:
        """Retrieves all active subscriptions for a given user."""
        with self.persistence as p:
            return p.get_subscriptions_by_chat_id(chat_id)

    def remove_subscription(self, subscription_id: int) -> None:
        """Marks a subscription as inactive (soft delete)."""
        with self.persistence as p:
            p.deactivate_subscription(subscription_id)

    def get_all_active_subscriptions(self) -> List[dict]:
        """Retrieves all active subscriptions from the database."""
        with self.persistence as p:
            return p.get_all_active_subscriptions()

    def update_last_notified(self, subscription_id: int, notification_date: str) -> None:
        """Updates the last_notified date for a subscription."""
        with self.persistence as p:
            p.update_subscription_last_notified(subscription_id, notification_date)
