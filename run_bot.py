"""
This script runs the Telegram bot and the notification scheduler.
"""
import asyncio
import logging
import sqlite3
from datetime import datetime
from telegram.ext import Application, AIORateLimiter

from schedule_parser.config import TELEGRAM_BOT_TOKEN
from schedule_parser.db_manager import init_db
from telegram_bot.bot import main as bot_main
from telegram_bot.scheduler import scheduler
from telegram_bot.logging_config import setup_database_logging
from build_cache import build_address_database

# Initialize the main database and configure logging
init_db()
setup_database_logging()

logger = logging.getLogger(__name__)


def record_bot_start_time():
    """Records the bot's start time in the system_info table."""
    conn = sqlite3.connect("waste_schedule.db")
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO system_info (key, value) VALUES (?, ?)",
        ("bot_start_time", datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


async def main():
    """Initializes and runs the bot and scheduler."""
    # Build the address cache database
    build_address_database()

    # Record the bot start time
    record_bot_start_time()

    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set.")
        return

    # Configure rate limiting
    rate_limiter = AIORateLimiter(
        overall_max_rate=30,  # Corresponds to the bulk notification limit
        group_max_rate=20 / 60,  # 20 messages per minute in any single group
        max_rate=1,  # 1 message per second in any single chat
    )

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).rate_limiter(rate_limiter).build()

    # Setup handlers in bot_main
    bot_main(TELEGRAM_BOT_TOKEN, application)

    # Run the scheduler and bot polling concurrently
    await asyncio.gather(
        scheduler(application.bot),
        application.run_polling()
    )

if __name__ == "__main__":
    asyncio.run(main())
