import argparse
import asyncio
import logging

from dashboard.app import run_dashboard
from schedule_parser.address_cache import build_address_database
from telegram_bot.bot import main as run_bot

from .app_factory import create_facade, initialize_app

logger = logging.getLogger(__name__)


def main():
    initialize_app()
    parser = argparse.ArgumentParser(description="DumpDate application runner.")
    parser.add_argument(
        "command",
        choices=["bot", "dashboard", "build-cache"],
        help="The command to execute.",
    )
    args = parser.parse_args()

    if args.command == "build-cache":
        logger.info("Building address cache...")
        build_address_database()
        return

    facade = create_facade()

    if args.command == "bot":
        logger.info("Starting bot...")
        asyncio.run(run_bot(facade))
    elif args.command == "dashboard":
        logger.info("Starting dashboard...")
        run_dashboard(facade)


if __name__ == "__main__":
    main()
