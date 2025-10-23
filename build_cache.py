"""
This script builds the address lookup cache from the Dresden OGC API.

It is a standalone script that should be run periodically to keep the address
data up-to-date.
"""
import logging
from schedule_parser.address_cache import build_address_database

if __name__ == "__main__":
    # Configure logging for the script
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    build_address_database()
