"""
This module provides an address lookup mechanism backed by a SQLite database.
"""
import logging
import sqlite3
import requests
import os
import json

from .config import ADDRESS_DB_FILE, ADDRESS_API_URL
from .database import get_db_connection

# Get a logger instance for this module
logger = logging.getLogger(__name__)


def build_address_database(db_path: str = ADDRESS_DB_FILE):
    """
    Downloads the full address dataset and populates a SQLite database with
    an indexed address-to-ID lookup table.

    This script should be run periodically (e.g., weekly) to keep the
    address data up-to-date.

    Args:
        db_path: The path to the SQLite database file.
    """
    logger.info(f"Building address cache database at '{db_path}'...")

    # Remove the old database file if it exists to ensure a fresh build
    if os.path.exists(db_path):
        os.remove(db_path)
        logger.info(f"Removed existing database file: {db_path}")

    logger.info(f"Attempting to download data from: {ADDRESS_API_URL}")
    try:
        response = requests.get(ADDRESS_API_URL, timeout=60)
        response.raise_for_status()
        data = response.json()
        logger.info("Successfully downloaded and parsed address data.")

        features = data.get("features", [])
        if not features:
            logger.error("No 'features' found in the downloaded data.")
            return

        address_data = []
        for feature in features:
            props = feature.get("properties", {})
            address = props.get("adresse")
            feature_id = feature.get("id")
            if address and feature_id is not None:
                address_data.append((address.lower().strip(), feature_id))

        if not address_data:
            logger.error("Could not extract any address-ID pairs.")
            return

        logger.info(f"Extracted {len(address_data)} address-ID pairs.")

        with get_db_connection(db_path) as (conn, cursor):
            cursor.execute("CREATE TABLE addresses (address TEXT PRIMARY KEY, address_id INTEGER NOT NULL)")
            cursor.executemany("INSERT INTO addresses VALUES (?, ?)", address_data)

        logger.info(f"Successfully created and populated address database: {db_path}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download address data: {e}")
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON from the API response.")
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")


def get_address_id(address: str, db_path: str = ADDRESS_DB_FILE) -> int:
    """
    Finds the address ID from the SQLite database.

    Args:
        address: The address to search for.
        db_path: The path to the SQLite database file.

    Returns:
        The ID of the address.

    Raises:
        ValueError: If the address is not found.
        FileNotFoundError: If the database file has not been created.
    """
    try:
        with get_db_connection(db_path) as (conn, cursor):
            normalized_address = address.lower().strip()
            cursor.execute("SELECT address_id FROM addresses WHERE address = ?", (normalized_address,))
            result = cursor.fetchone()

            if result:
                address_id = result[0]
                logger.info(f"Found address ID {address_id} for '{address}' in DB.")
                return address_id
            else:
                logger.warning(f"Address '{address}' not found in the database.")
                raise ValueError(f"Address not found: {address}")

    except sqlite3.OperationalError as e:
        logger.error(f"Database error, likely the DB file is missing. Run the build_cache.py script. Error: {e}")
        raise FileNotFoundError(f"Database file '{db_path}' not found.") from e
