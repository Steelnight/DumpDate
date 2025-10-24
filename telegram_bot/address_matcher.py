"""
This module handles matching user-provided addresses against the address database.
"""
import sqlite3
from typing import List, Tuple
from thefuzz import process
from schedule_parser.config import ADDRESS_LOOKUP_DB_PATH

def find_address_matches(query: str, db_path: str = ADDRESS_LOOKUP_DB_PATH) -> List[Tuple[str, int]]:
    """
    Finds address matches for a given query, first trying an exact match,
    then falling back to fuzzy matching.
    """
    conn = sqlite3.connect(db_path)
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
    conn.close()

    matches = process.extractBests(query, all_addresses, limit=5, score_cutoff=80)

    if not matches:
        return []

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    results = []
    for match, score in matches:
        cur.execute("SELECT address, address_id FROM addresses WHERE address = ?", (match,))
        result = cur.fetchone()
        if result:
            results.append(result)

    conn.close()
    return results

def get_address_by_id(address_id: int, db_path: str = ADDRESS_LOOKUP_DB_PATH) -> str | None:
    """Retrieves an address by its ID."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT address FROM addresses WHERE address_id = ?", (address_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None
