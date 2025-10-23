"""
This module provides functionality for downloading iCal files.

It uses the Dresden iCal API to fetch the iCal files.
"""
import logging
import tempfile
from datetime import date
from typing import Optional

import requests

# Get a logger instance for this module
logger = logging.getLogger(__name__)

from .config import ICAL_API_URL


def download_ical_file(
    standort_id: int, start_date: date, end_date: date
) -> Optional[str]:
    """
    Downloads the iCal file for a given location and date range.

    Args:
        standort_id: The ID of the location (STANDORT).
        start_date: The start date of the date range.
        end_date: The end date of the date range.

    Returns:
        The path to the downloaded temporary file, or None on error.
    """
    params = {
        "STANDORT": standort_id,
        "DATUM_VON": start_date.strftime("%d.%m.%Y"),
        "DATUM_BIS": end_date.strftime("%d.%m.%Y"),
    }

    try:
        response = requests.get(ICAL_API_URL, params=params, timeout=10)
        response.raise_for_status()

        # Create a temporary file to store the ICS content
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".ics", encoding="utf-8"
        ) as temp_file:
            temp_file.write(response.text)
            file_path = temp_file.name

        logger.info(f"Successfully downloaded iCal file to {file_path}")
        return file_path

    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading iCal file for STANDORT {standort_id}: {e}")
        return None
