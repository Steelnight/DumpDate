import logging
from datetime import date
from schedule_parser.facade import get_schedule_for_address

# --- Configuration ---
# Configure logging to display INFO level messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Example Address: A known valid address in Dresden
TARGET_ADDRESS = "Chemnitzer Straße 42"

# Date Range: Fetch schedule for the entire year of 2026
START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 12, 31)

# Database Path: Where the schedule data will be stored.
DB_PATH = "waste_schedule_example.db"

def main():
    """
    An example function to demonstrate fetching the waste schedule for a specific address.
    """
    logging.info(f"--- Waste Schedule Fetcher ---")
    logging.info(f"Target Address: {TARGET_ADDRESS}")
    logging.info(f"Date Range: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
    logging.info(f"Database: {DB_PATH}")

    get_schedule_for_address(
        address=TARGET_ADDRESS,
        start_date=START_DATE,
        end_date=END_DATE,
        db_path=DB_PATH
    )

    logging.info("Process finished. Check the database file for the schedule.")

if __name__ == "__main__":
    main()
