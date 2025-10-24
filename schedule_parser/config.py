"""
This module contains configuration settings for the application.
"""
import os
import logging

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Schedule update interval in hours
SCHEDULE_UPDATE_INTERVAL_HOURS = int(os.environ.get("SCHEDULE_UPDATE_INTERVAL_HOURS", 24))

# Logging level
LOG_LEVEL = logging.INFO

# Database paths
WASTE_SCHEDULE_DB_PATH = os.environ.get("WASTE_SCHEDULE_DB_PATH", "waste_schedule.db")
ADDRESS_LOOKUP_DB_PATH = os.environ.get("ADDRESS_LOOKUP_DB_PATH", "address_lookup.db")

# API URLs
ADDRESS_API_URL = os.environ.get("ADDRESS_API_URL", "https://kommisdd.dresden.de/net4/public/ogcapi/collections/L134/items?limit=100000")
ICAL_API_URL = os.environ.get("ICAL_API_URL", "https://stadtplan.dresden.de/project/cardo3Apps/IDU_DDStadtplan/abfall/ical.ashx")

# Telegram bot rate limiting
TELEGRAM_RATE_LIMIT_OVERALL = int(os.environ.get("TELEGRAM_RATE_LIMIT_OVERALL", 30))
TELEGRAM_RATE_LIMIT_GROUP = float(os.environ.get("TELEGRAM_RATE_LIMIT_GROUP", 20 / 60))
TELEGRAM_RATE_LIMIT_PER_CHAT = int(os.environ.get("TELEGRAM_RATE_LIMIT_PER_CHAT", 1))

# Schedule service retry settings
SCHEDULE_SERVICE_MAX_RETRIES = int(os.environ.get("SCHEDULE_SERVICE_MAX_RETRIES", 3))
SCHEDULE_SERVICE_RETRY_DELAY = int(os.environ.get("SCHEDULE_SERVICE_RETRY_DELAY", 10))
