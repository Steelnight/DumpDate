"""
This module provides an address lookup mechanism backed by a SQLite database.
"""
import logging
import sqlite3

from .config import ADDRESS_DB_FILE
from .database import get_db_connection

# Get a logger instance for this module
logger = logging.getLogger(__name__)


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
