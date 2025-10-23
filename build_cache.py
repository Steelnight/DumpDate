import sqlite3
import json
import logging
import requests
import os

from schedule_parser.config import ADDRESS_API_URL, ADDRESS_DB_FILE
from schedule_parser.database import get_db_connection


def build_address_database(db_path: str = ADDRESS_DB_FILE):
    """
    Downloads the full address dataset and populates a SQLite database with
    an indexed address-to-ID lookup table.

    This script should be run periodically (e.g., weekly) to keep the
    address data up-to-date.

    Args:
        db_path: The path to the SQLite database file.
    """
    logging.info(f"Building address cache database at '{db_path}'...")

    # Remove the old database file if it exists to ensure a fresh build
    if os.path.exists(db_path):
        os.remove(db_path)
        logging.info(f"Removed existing database file: {db_path}")

    logging.info(f"Attempting to download data from: {ADDRESS_API_URL}")
    try:
        response = requests.get(ADDRESS_API_URL, timeout=60)
        response.raise_for_status()
        data = response.json()
        logging.info("Successfully downloaded and parsed address data.")

        features = data.get("features", [])
        if not features:
            logging.error("No 'features' found in the downloaded data.")
            return

        address_data = []
        for feature in features:
            props = feature.get("properties", {})
            address = props.get("adresse")
            feature_id = feature.get("id")
            if address and feature_id is not None:
                address_data.append((address.lower().strip(), feature_id))

        if not address_data:
            logging.error("Could not extract any address-ID pairs.")
            return

        logging.info(f"Extracted {len(address_data)} address-ID pairs.")

        with get_db_connection(db_path) as (conn, cursor):
            cursor.execute("CREATE TABLE addresses (address TEXT PRIMARY KEY, address_id INTEGER NOT NULL)")
            cursor.executemany("INSERT INTO addresses VALUES (?, ?)", address_data)

        logging.info(f"Successfully created and populated address database: {db_path}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download address data: {e}")
    except json.JSONDecodeError:
        logging.error("Failed to parse JSON from the API response.")
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")

if __name__ == "__main__":
    # Configure logging for the script
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    build_address_database()
