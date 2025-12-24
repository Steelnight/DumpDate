import json
import logging
import os
import sqlite3

import requests

from schedule_parser.config import ADDRESS_API_URL, ADDRESS_LOOKUP_DB_PATH

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def build_address_database():
    """
    Downloads the full address dataset and populates a SQLite database with
    an indexed address-to-ID lookup table.

    This script should be run periodically (e.g., weekly) to keep the
    address data up-to-date.
    """
    logging.info(f"Building address cache database at '{ADDRESS_LOOKUP_DB_PATH}'...")

    # Remove the old database file if it exists to ensure a fresh build
    if os.path.exists(ADDRESS_LOOKUP_DB_PATH):
        os.remove(ADDRESS_LOOKUP_DB_PATH)
        logging.info(f"Removed existing database file: {ADDRESS_LOOKUP_DB_PATH}")

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

        conn = sqlite3.connect(ADDRESS_LOOKUP_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "DROP TABLE IF EXISTS addresses"
        )
        cursor.execute(
            "CREATE TABLE addresses (address TEXT PRIMARY KEY, address_id INTEGER NOT NULL)"
        )
        cursor.executemany("INSERT INTO addresses VALUES (?, ?)", address_data)

        conn.commit()
        conn.close()

        logging.info(
            f"Successfully created and populated address database: {ADDRESS_LOOKUP_DB_PATH}"
        )

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download address data: {e}")
    except json.JSONDecodeError:
        logging.error("Failed to parse JSON from the API response.")
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
