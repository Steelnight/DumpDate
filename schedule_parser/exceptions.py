"""
This module defines custom exceptions for the waste schedule parser.
"""


class DownloadError(Exception):
    """Custom exception for errors during iCal file download."""

    pass


class ParsingError(Exception):
    """Custom exception for errors during iCal file parsing."""

    pass
