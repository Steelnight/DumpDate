"""
This module defines a custom context class for the Telegram bot.
"""
from telegram.ext import CallbackContext, ExtBot

from schedule_parser.facade import WasteManagementFacade


class CustomContext(CallbackContext[ExtBot, dict, dict, dict]):
    """
    A custom context class that holds the WasteManagementFacade instance.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._facade = None

    @property
    def facade(self) -> WasteManagementFacade:
        """
        The WasteManagementFacade instance.
        """
        return self._facade

    @facade.setter
    def facade(self, value: WasteManagementFacade):
        """
        Sets the WasteManagementFacade instance.
        """
        self._facade = value
