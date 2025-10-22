import sqlite3
import json
import logging
import requests
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ADDRESS_API_URL = "https://kommisdd.dresden.de/net4/public/ogcapi/collections/L134/items?limit=100000"
DB_FILE = "address_lookup.db"

def build_address_database():
    """
    Downloads the full address dataset and populates a SQLite database with
    an indexed address-to-ID lookup table.

    This script should be run periodically (e.g., weekly) to keep the
    address data up-to-date.
    """
    logging.info(f"Building address cache database at '{DB_FILE}'...")

    # Remove the old database file if it exists to ensure a fresh build
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        logging.info(f"Removed existing database file: {DB_FILE}")

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

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE addresses (address TEXT PRIMARY KEY, address_id INTEGER NOT NULL)")
        cursor.executemany("INSERT INTO addresses VALUES (?, ?)", address_data)

        conn.commit()
        conn.close()

        logging.info(f"Successfully created and populated address database: {DB_FILE}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download address data: {e}")
    except json.JSONDecodeError:
        logging.error("Failed to parse JSON from the API response.")
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")

if __name__ == "__main__":
    build_address_database()
