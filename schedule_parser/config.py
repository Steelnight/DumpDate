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
