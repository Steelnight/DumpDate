"""
This module handles database interactions for the waste schedule parser.

It provides functions for initializing the database schema and upserting events.
"""
import sqlite3

from .models import WasteEvent
from .database import get_db_connection
from .config import SCHEDULE_DB_FILE


def init_db(db_path: str = SCHEDULE_DB_FILE) -> None:
    """Initialize SQLite schema if not exists."""
    with get_db_connection(db_path) as (conn, cur):
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS waste_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid TEXT UNIQUE,
                date TEXT,
                location TEXT,
                waste_type TEXT,
                contact_name TEXT,
                contact_phone TEXT,
                hash TEXT,
                original_address TEXT
            )
        """
        )


def upsert_event(event: WasteEvent, db_path: str = SCHEDULE_DB_FILE) -> None:
    """Insert or update event following deduplication logic."""
    with get_db_connection(db_path) as (conn, cur):
        event_hash = event.compute_hash()

        # Check by UID
        cur.execute("SELECT hash FROM waste_events WHERE uid = ?", (event.uid,))
        row = cur.fetchone()

        if row:
            if row[0] != event_hash:
                cur.execute(
                    """
                    UPDATE waste_events
                    SET date=?, location=?, waste_type=?, contact_name=?, contact_phone=?, hash=?, original_address=?
                    WHERE uid=?
                """,
                    (
                        event.date,
                        event.location,
                        event.waste_type,
                        event.contact_name,
                        event.contact_phone,
                        event_hash,
                        event.original_address,
                        event.uid,
                    ),
                )
        else:
            # Check for existing hash with different UID
            cur.execute("SELECT uid FROM waste_events WHERE hash = ?", (event_hash,))
            if not cur.fetchone():
                cur.execute(
                    """
                    INSERT INTO waste_events (uid, date, location, waste_type, contact_name, contact_phone, hash, original_address)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        event.uid,
                        event.date,
                        event.location,
                        event.waste_type,
                        event.contact_name,
                        event.contact_phone,
                        event_hash,
                        event.original_address,
                    ),
                )
