"""
This module provides functionality for parsing iCal files.

It uses the icalendar library to parse the iCal files.
"""
import logging
import re

from icalendar import Calendar

from .models import WasteEvent

# Get a logger instance for this module
logger = logging.getLogger(__name__)

waste_type_pattern = re.compile(
    r"(Bio|Gelbe|Rest|Papier|Weihnachtsbaum)[-\s]?Tonne", re.IGNORECASE
)
contact_pattern = re.compile(r"durch (.*?),\s*Kontakt:\s*([\d\s\/\+()-]+?)\)")


def parse_ics(ics_text: str, original_address: str) -> list[WasteEvent]:
    """Parse an ICS file and return a list of WasteEvent objects."""
    events = []
    try:
        cal = Calendar.from_ical(ics_text)
    except ValueError as e:
        logger.warning(f"Failed to parse ICS file: {e}")
        return events

    for component in cal.walk("VEVENT"):
        try:
            uid = str(component.get("UID"))
            # Correctly handle date extraction
            dt_start = component.get("DTSTART")
            if dt_start is None:
                logger.warning(
                    f"Skipping event with UID {uid} due to missing DTSTART."
                )
                continue

            # The .dt attribute holds the date or datetime object
            date = dt_start.dt.strftime("%Y-%m-%d")

            location = str(component.get("LOCATION", "")).strip()
            description = (
                str(component.get("DESCRIPTION", ""))
                .replace("\\n", "\n")
                .replace("\\\\", "\\")
                .strip()
            )
            summary = str(component.get("SUMMARY", "")).strip()

            # Waste type via regex from summary
            match = waste_type_pattern.search(summary)
            if not match and description:  # Fallback to description if not in summary
                match = waste_type_pattern.search(description)

            # Normalize waste_type capitalization
            if match:
                # Reconstruct with normalized capitalization, e.g., "Bio-Tonne"
                waste_type = match.group(1).capitalize()
                # Check if the separator is present
                separator = "-" if "-" in match.group(0) else " "
                waste_type += f"{separator}Tonne"
            else:
                waste_type = "Unbekannt"

            # Contact info from description
            c_match = contact_pattern.search(description)
            contact_name = c_match.group(1).strip() if c_match else ""
            contact_phone = c_match.group(2).strip() if c_match else ""

            events.append(
                WasteEvent(
                    uid=uid,
                    date=date,
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
