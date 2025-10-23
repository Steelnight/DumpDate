"""
This module handles database interactions for the waste schedule parser.

It provides functions for initializing the database schema and upserting events.
"""
import sqlite3

from .models import WasteEvent


def init_db(db_path: str = "waste_schedule.db") -> None:
    """Initialize SQLite schema if not exists."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
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
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            address_id INTEGER NOT NULL,
            notification_time TEXT NOT NULL,
            last_notified DATE,
            UNIQUE(chat_id, address_id)
        )
    """
    )
    conn.commit()
    conn.close()


def upsert_event(event: WasteEvent, db_path: str = "waste_schedule.db") -> None:
    """Insert or update event following deduplication logic."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
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
    conn.commit()
    conn.close()
