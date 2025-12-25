import logging
import os
import sqlite3
import sys
from datetime import date, timedelta
import random
import concurrent.futures

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from schedule_parser.address_cache import build_address_database
from schedule_parser.config import ADDRESS_LOOKUP_DB_PATH
from schedule_parser.services.schedule_service import ScheduleService

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def check_address(address_info):
    address, address_id = address_info
    schedule_service = ScheduleService()
    start_date = date.today()
    end_date = start_date + timedelta(days=30)

    try:
        events = schedule_service.download_and_parse_schedule(
            standort_id=address_id,
            start_date=start_date,
            end_date=end_date,
            original_address=address
        )
        return (True, f"PASS: {address} (ID: {address_id}) - Found {len(events)} events")
    except Exception as e:
        return (False, f"FAIL: {address} (ID: {address_id}) - Error: {e}")

def main():
    # 1. Ensure Address Database Exists
    if not os.path.exists(ADDRESS_LOOKUP_DB_PATH):
        logger.info(f"Address database not found at {ADDRESS_LOOKUP_DB_PATH}. Building it now...")
        build_address_database()
    else:
        logger.info(f"Using existing address database at {ADDRESS_LOOKUP_DB_PATH}")

    # 2. Select 100 Real Addresses
    try:
        conn = sqlite3.connect(ADDRESS_LOOKUP_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT address, address_id FROM addresses")
        all_addresses = cursor.fetchall()
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Failed to read from address database: {e}")
        return

    if not all_addresses:
        logger.error("Address database is empty.")
        return

    # Randomly select 100 addresses (or less if not enough data)
    sample_size = min(100, len(all_addresses))
    test_samples = random.sample(all_addresses, sample_size)

    logger.info(f"Selected {len(test_samples)} addresses for testing.")
    logger.info(f"Testing schedule retrieval from {date.today()} to {date.today() + timedelta(days=30)}...")

    success_count = 0

    print("\n--- Test Results ---")

    # Use ThreadPoolExecutor to run requests concurrently
    # Max workers = 20 should be safe enough not to get IP banned while being fast
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_address = {executor.submit(check_address, addr): addr for addr in test_samples}
        for future in concurrent.futures.as_completed(future_to_address):
            success, message = future.result()
            print(message)
            if success:
                success_count += 1

    print("\n--- Summary ---")
    print(f"Total Addresses Tested: {len(test_samples)}")
    print(f"Successful Retrievals: {success_count}")
    print(f"Failed Retrievals: {len(test_samples) - success_count}")
    print(f"Success Rate: {success_count / len(test_samples) * 100:.2f}%")

if __name__ == "__main__":
    main()
