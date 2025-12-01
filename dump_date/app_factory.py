"""
This module provides a factory for creating and configuring the application's core components.
"""

from schedule_parser.facade import WasteManagementFacade
from schedule_parser.services.address_service import AddressService
from schedule_parser.services.notification_service import NotificationService
from schedule_parser.services.persistence_service import PersistenceService
from schedule_parser.services.schedule_service import ScheduleService
from schedule_parser.services.smart_schedule_service import \
    SmartScheduleService
from schedule_parser.services.subscription_service import SubscriptionService

from .logging_config import setup_database_logging


def initialize_app():
    """
    Initializes the application by setting up logging and the database.
    """
    setup_database_logging()
    # Initialize the main database
    with PersistenceService() as persistence_service:
        persistence_service.init_db()


def create_facade() -> WasteManagementFacade:
    """
    Initializes and returns the WasteManagementFacade with all its dependencies.
    """
    address_service = AddressService()
    persistence_service = PersistenceService()
    schedule_service = ScheduleService()
    subscription_service = SubscriptionService(persistence_service)
    notification_service = NotificationService(persistence_service)
    smart_schedule_service = SmartScheduleService(
        persistence_service=persistence_service, schedule_service=schedule_service
    )

    facade = WasteManagementFacade(
        address_service=address_service,
        schedule_service=schedule_service,
        persistence_service=persistence_service,
        subscription_service=subscription_service,
        notification_service=notification_service,
        smart_schedule_service=smart_schedule_service,
    )
    return facade
