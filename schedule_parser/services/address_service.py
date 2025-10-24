"""
This module defines the AddressService for looking up address IDs.
"""
import logging
import sqlite3
from typing import List, Tuple
from thefuzz import process

# Get a logger instance for this module
logger = logging.getLogger(__name__)


class AddressService:
    """Handles address lookups and caching."""

    def __init__(self, db_path: str = "address_lookup.db"):
        """
        Initializes the AddressService.

        Args:
            db_path: The path to the address lookup SQLite database.
        """
        self.db_path = db_path

    def get_address_id(self, address: str) -> int:
        """
        Finds the address ID from the SQLite database using an exact match.

        Args:
            address: The address to search for.

        Returns:
            The ID of the address.

        Raises:
            ValueError: If the address is not found.
            FileNotFoundError: If the database file has not been created.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
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
            raise FileNotFoundError(f"Database file '{self.db_path}' not found.") from e

    def find_address_matches(self, query: str) -> List[Tuple[str, int]]:
        """
        Finds address matches for a given query, first trying an exact match,
        then falling back to fuzzy matching.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            # Try exact match first
            cur.execute("SELECT address, address_id FROM addresses WHERE address = ?", (query.lower().strip(),))
            exact_match = cur.fetchone()
            if exact_match:
                conn.close()
                return [exact_match]

            # Fuzzy matching fallback
            cur.execute("SELECT address FROM addresses")
            all_addresses = [row[0] for row in cur.fetchall()]

            matches = process.extractBests(query, all_addresses, limit=5, score_cutoff=80)

            if not matches:
                conn.close()
                return []

            results = []
            for match, score in matches:
                cur.execute("SELECT address, address_id FROM addresses WHERE address = ?", (match,))
                result = cur.fetchone()
                if result:
                    results.append(result)

            conn.close()
            return results
        except sqlite3.OperationalError as e:
            logger.error(f"Database error while finding matches: {e}")
            raise FileNotFoundError(f"Database file '{self.db_path}' not found.") from e
