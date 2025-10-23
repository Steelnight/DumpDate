"""
This module contains the configuration for the schedule_parser.
"""

# The API endpoint for fetching address data from the Dresden OGC API.
# The 'limit' parameter is set to a high value to ensure all addresses are retrieved.
ADDRESS_API_URL = "https://kommisdd.dresden.de/net4/public/ogcapi/collections/L134/items?limit=100000"

# The file path for the SQLite database that stores the address-to-ID lookup cache.
# This database is created and populated by the 'build_cache.py' script.
ADDRESS_DB_FILE = "address_lookup.db"

# The base URL for downloading iCalendar (.ics) files for waste schedules.
# It requires 'STANDORT', 'DATUM_VON', and 'DATUM_BIS' as query parameters.
ICAL_API_URL = "https://stadtplan.dresden.de/project/cardo3Apps/IDU_DDStadtplan/abfall/ical.ashx"

# The default file path for the SQLite database where the parsed waste schedule events are stored.
SCHEDULE_DB_FILE = "waste_schedule.db"
