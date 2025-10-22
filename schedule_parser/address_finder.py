"""
This module provides an address lookup mechanism backed by a SQLite database.
"""
import logging
import sqlite3

# --- Globals ---
DB_FILE = "address_lookup.db"

# Get a logger instance for this module
logger = logging.getLogger(__name__)


def get_address_id(address: str) -> int:
    """
    Finds the address ID from the SQLite database.

    Args:
        address: The address to search for.

    Returns:
        The ID of the address.

    Raises:
        ValueError: If the address is not found.
        FileNotFoundError: If the database file has not been created.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Normalize the input address for lookup
        normalized_address = address.lower().strip()

        cursor.execute("SELECT address_id FROM addresses WHERE address = ?", (normalized_address,))
        result = cursor.fetchone()

        conn.close()

        if result:
            address_id = result[0]
            logger.info(f"Found address ID {address_id} for '{address}' in DB.")
            return address_id
        else:
            logger.warning(f"Address '{address}' not found in the database.")
            raise ValueError(f"Address not found: {address}")

    except sqlite3.OperationalError as e:
        logger.error(f"Database error, likely the DB file is missing. Run the build_cache.py script. Error: {e}")
        raise FileNotFoundError(f"Database file '{DB_FILE}' not found.") from e
