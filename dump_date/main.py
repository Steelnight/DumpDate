import argparse
import asyncio
import logging

from telegram_bot.bot import main as run_bot
from .app_factory import create_facade, initialize_app

# DELETE the global import:
# from dashboard.app import run_dashboard 

logger = logging.getLogger(__name__)

def main():
    initialize_app()
    parser = argparse.ArgumentParser(description="DumpDate application runner.")
    parser.add_argument(
        "command",
        choices=["bot", "dashboard"],
        help="The command to execute.",
    )
    args = parser.parse_args()

    facade = create_facade()

    if args.command == "bot":
        logger.info("Starting bot...")
        asyncio.run(run_bot(facade))
    elif args.command == "dashboard":
        # MOVE the import here:
        from dashboard.app import run_dashboard
        logger.info("Starting dashboard...")
        run_dashboard(facade)

if __name__ == "__main__":
    main()
