"""
This module defines the ScheduleService for downloading and parsing iCal files.
"""
import logging
import re
import time
from datetime import date
from typing import List

import requests
from icalendar import Calendar

from ..exceptions import DownloadError, ParsingError
from ..models import WasteEvent

# Get a logger instance for this module
logger = logging.getLogger(__name__)

ICAL_API_URL = "https://stadtplan.dresden.de/project/cardo3Apps/IDU_DDStadtplan/abfall/ical.ashx"

waste_type_pattern = re.compile(
    r"(Bio|Gelbe|Rest|Papier|Weihnachtsbaum)[-\s]?Tonne", re.IGNORECASE
)
contact_pattern = re.compile(r"durch (.*?),\s*Kontakt:\s*([\d\s\/\+()-]+?)\)")


class ScheduleService:
    """Handles downloading and parsing of waste schedules."""

    def __init__(self, max_retries: int = 3, retry_delay: int = 10):
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def download_and_parse_schedule(
        self, standort_id: int, start_date: date, end_date: date, original_address: str
    ) -> List[WasteEvent]:
        """
        Downloads and parses the iCal file for a given location and date range.

        Args:
            standort_id: The ID of the location (STANDORT).
            start_date: The start date of the date range.
            end_date: The end date of the date range.
            original_address: The original address string to associate with the events.

        Returns:
            A list of WasteEvent objects.

        Raises:
            DownloadError: If the iCal file cannot be downloaded after retries.
            ParsingError: If the downloaded iCal content cannot be parsed.
        """
        for attempt in range(self.max_retries):
            try:
                ics_text = self._download_ical_text(standort_id, start_date, end_date)
                events = self._parse_ics(ics_text, original_address)
                return events
            except (DownloadError, ParsingError) as e:
                logger.warning(
                    f"Attempt {attempt + 1} failed for location {standort_id}. Error: {e}"
                )
                if attempt + 1 == self.max_retries:
                    logger.error(
                        f"All {self.max_retries} download attempts failed for location {standort_id}."
                    )
                    raise
                time.sleep(self.retry_delay)
        return []  # Should be unreachable

    def _download_ical_text(
        self, standort_id: int, start_date: date, end_date: date
    ) -> str:
        """Downloads the iCal content as a string."""
        params = {
            "STANDORT": standort_id,
            "DATUM_VON": start_date.strftime("%d.%m.%Y"),
            "DATUM_BIS": end_date.strftime("%d.%m.%Y"),
        }
        try:
            response = requests.get(ICAL_API_URL, params=params, timeout=10)
            response.raise_for_status()
            logger.info(f"Successfully downloaded iCal data for STANDORT {standort_id}")
            return response.text
        except requests.exceptions.RequestException as e:
            raise DownloadError(
                f"Error downloading iCal file for STANDORT {standort_id}: {e}"
            ) from e

    def _parse_ics(self, ics_text: str, original_address: str) -> List[WasteEvent]:
        """Parse an ICS file and return a list of WasteEvent objects."""
        events = []
        try:
            cal = Calendar.from_ical(ics_text)
        except ValueError as e:
            raise ParsingError(f"Failed to parse ICS file: {e}") from e

        for component in cal.walk("VEVENT"):
            try:
                uid = str(component.get("UID"))
                dt_start = component.get("DTSTART")
                if dt_start is None:
                    logger.warning(f"Skipping event with UID {uid} due to missing DTSTART.")
                    continue

                event_date = dt_start.dt.strftime("%Y-%m-%d")
                location = str(component.get("LOCATION", "")).strip()
                description = (
                    str(component.get("DESCRIPTION", "")).replace("\\n", "\n").replace("\\\\", "\\").strip()
                )
                summary = str(component.get("SUMMARY", "")).strip()

                match = waste_type_pattern.search(summary)
                if not match and description:
                    match = waste_type_pattern.search(description)

                if match:
                    waste_type = match.group(1).capitalize()
                    separator = "-" if "-" in match.group(0) else " "
                    waste_type += f"{separator}Tonne"
                else:
                    waste_type = "Unbekannt"

                c_match = contact_pattern.search(description)
                contact_name = c_match.group(1).strip() if c_match else ""
                contact_phone = c_match.group(2).strip() if c_match else ""

                events.append(
                    WasteEvent(
                        uid=uid,
                        date=event_date,
                        location=location,
                        waste_type=waste_type,
                        contact_name=contact_name,
                        contact_phone=contact_phone,
                        original_address=original_address,
                    )
                )
            except Exception as e:
                uid = component.get("UID", "Unknown UID")
                logger.warning(f"Skipping event with UID {uid} due to an error: {e}")
                continue
        return events
