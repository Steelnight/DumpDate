"""
This module defines the PersistenceService for database interactions.
"""

import sqlite3
from typing import List, Optional

from ..config import WASTE_SCHEDULE_DB_PATH
from ..models import WasteEvent


class PersistenceService:
    """Handles all database interactions for the application."""

    def __init__(self, db_path: str = WASTE_SCHEDULE_DB_PATH):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._cursor: Optional[sqlite3.Cursor] = None

    def __enter__(self) -> "PersistenceService":
        """Establishes the database connection."""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._cursor = self._conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Commits changes and closes the connection."""
        if self._conn:
            self._conn.commit()
            self._conn.close()

    def _get_cursor(self) -> sqlite3.Cursor:
        """Returns the cursor, ensuring the connection is open."""
        if self._cursor is None:
            raise RuntimeError("Database connection is not open. Use 'with' statement.")
        return self._cursor

    def init_db(self) -> None:
        """Initialize SQLite schema if not exists."""
        cur = self._get_cursor()
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
                original_address TEXT,
                address_id INTEGER
            )
        """
        )
        # Attempt to add address_id column to waste_events if it doesn't exist
        try:
            cur.execute("ALTER TABLE waste_events ADD COLUMN address_id INTEGER")
        except sqlite3.OperationalError:
            # Column likely already exists
            pass

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                address_id INTEGER NOT NULL,
                address_name TEXT,
                notification_time TEXT NOT NULL,
                last_notified DATE,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(chat_id, address_id)
            )
        """
        )
        # Attempt to add address_name column if it doesn't exist (migration for existing DBs)
        try:
            cur.execute("ALTER TABLE subscriptions ADD COLUMN address_name TEXT")
        except sqlite3.OperationalError:
            # Column likely already exists
            pass

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                logger_name TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS system_info (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS notification_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscription_id INTEGER,
                timestamp_scheduled DATETIME DEFAULT CURRENT_TIMESTAMP,
                timestamp_sent DATETIME,
                status TEXT NOT NULL,
                error_message TEXT,
                FOREIGN KEY(subscription_id) REFERENCES subscriptions(id)
            )
            """
        )

    def upsert_event(self, event: WasteEvent) -> None:
        """Insert or update event following deduplication logic."""
        cur = self._get_cursor()
        event_hash = event.compute_hash()
        cur.execute("SELECT hash FROM waste_events WHERE uid = ?", (event.uid,))
        row = cur.fetchone()
        if row:
            if row[0] != event_hash:
                cur.execute(
                    "UPDATE waste_events SET date=?, location=?, waste_type=?, contact_name=?, contact_phone=?, hash=?, original_address=?, address_id=? WHERE uid=?",
                    (
                        event.date,
                        event.location,
                        event.waste_type,
                        event.contact_name,
                        event.contact_phone,
                        event_hash,
                        event.original_address,
                        event.address_id,
                        event.uid,
                    ),
                )
        else:
            cur.execute("SELECT uid FROM waste_events WHERE hash = ?", (event_hash,))
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO waste_events (uid, date, location, waste_type, contact_name, contact_phone, hash, original_address, address_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        event.uid,
                        event.date,
                        event.location,
                        event.waste_type,
                        event.contact_name,
                        event.contact_phone,
                        event_hash,
                        event.original_address,
                        event.address_id,
                    ),
                )

    def find_subscription_by_chat_and_address(
        self, chat_id: int, address_id: int
    ) -> Optional[dict]:
        """Finds a subscription by chat_id and address_id."""
        cur = self._get_cursor()
        cur.execute(
            "SELECT * FROM subscriptions WHERE chat_id = ? AND address_id = ?",
            (chat_id, address_id),
        )
        return cur.fetchone()

    def reactivate_subscription(
        self, subscription_id: int, address_name: str, notification_time: str
    ) -> None:
        """Reactivates an existing subscription."""
        cur = self._get_cursor()
        cur.execute(
            "UPDATE subscriptions SET is_active = 1, address_name = ?, notification_time = ?, last_notified = NULL WHERE id = ?",
            (address_name, notification_time, subscription_id),
        )

    def create_subscription(
        self, chat_id: int, address_id: int, address_name: str, notification_time: str
    ) -> None:
        """Creates a new subscription."""
        cur = self._get_cursor()
        cur.execute(
            "INSERT INTO subscriptions (chat_id, address_id, address_name, notification_time, last_notified) VALUES (?, ?, ?, ?, NULL)",
            (chat_id, address_id, address_name, notification_time),
        )

    def get_subscriptions_by_chat_id(self, chat_id: int) -> List[dict]:
        """Retrieves all active subscriptions for a given chat_id."""
        cur = self._get_cursor()
        cur.execute(
            "SELECT id, address_id, address_name, notification_time FROM subscriptions WHERE chat_id = ? AND is_active = 1",
            (chat_id,),
        )
        return cur.fetchall()

    def deactivate_subscription(self, subscription_id: int) -> None:
        """Marks a subscription as inactive."""
        cur = self._get_cursor()
        cur.execute(
            "UPDATE subscriptions SET is_active = 0 WHERE id = ?", (subscription_id,)
        )

    def get_all_active_subscriptions(self) -> List[dict]:
        """Retrieves all active subscriptions from the database."""
        cur = self._get_cursor()
        cur.execute(
            "SELECT id, chat_id, address_id, address_name, notification_time, last_notified FROM subscriptions WHERE is_active = 1"
        )
        return cur.fetchall()

    def update_subscription_last_notified(
        self, subscription_id: int, notification_date: str
    ) -> None:
        """Updates the last_notified date for a subscription."""
        cur = self._get_cursor()
        cur.execute(
            "UPDATE subscriptions SET last_notified = ? WHERE id = ?",
            (notification_date, subscription_id),
        )

    def get_all_waste_events(self) -> List[dict]:
        """Retrieves all waste events from the database."""
        cur = self._get_cursor()
        cur.execute("SELECT * FROM waste_events")
        return cur.fetchall()

    def get_address_by_id(self, address_id: int) -> Optional[str]:
        """
        Retrieves an address string for a given address_id.
        Since we no longer have a global address DB, we try to find a name from subscriptions
        or fallback to 'Location <ID>'.
        """
        cur = self._get_cursor()
        # Try to find any active subscription with this address_id to get a user-friendly name
        cur.execute("SELECT address_name FROM subscriptions WHERE address_id = ? AND address_name IS NOT NULL LIMIT 1", (address_id,))
        row = cur.fetchone()
        if row:
            return row[0]

        return f"Location {address_id}"

    def create_notification_log(self, subscription_id: int, status: str) -> int:
        """Creates a new notification log entry and returns its ID."""
        cur = self._get_cursor()
        cur.execute(
            "INSERT INTO notification_logs (subscription_id, status) VALUES (?, ?)",
            (subscription_id, status),
        )
        return cur.lastrowid

    def update_notification_log_status(
        self, log_id: int, status: str, error_message: Optional[str] = None
    ) -> None:
        """Updates the status of a notification log."""
        cur = self._get_cursor()
        cur.execute(
            "UPDATE notification_logs SET status = ?, error_message = ?, timestamp_sent = CURRENT_TIMESTAMP WHERE id = ?",
            (status, error_message, log_id),
        )
        self._conn.commit()

    def get_all_logs(self) -> List[dict]:
        """Retrieves all logs from the database, ordered by timestamp descending."""
        cur = self._get_cursor()
        cur.execute(
            "SELECT * FROM logs ORDER BY timestamp DESC LIMIT 100"
        )  # Limit to 100 to avoid overwhelming the dashboard
        return cur.fetchall()

    def get_unique_subscribed_locations(self) -> List[dict]:
        """
        Retrieves a list of unique locations (address and address_id)
        that have at least one active subscription.
        """
        cur = self._get_cursor()

        query = """
            SELECT DISTINCT
                address_id,
                address_name as address
            FROM
                subscriptions
            WHERE
                is_active = 1
            GROUP BY address_id;
        """

        cur.execute(query)
        # We pick one name for the address_id. Since we grouped by address_id, it will return one row per ID.
        return [dict(row) for row in cur.fetchall()]

    def get_next_waste_event_for_subscription(
        self, address_id: int, today_date: str
    ) -> Optional[dict]:
        """
        Retrieves the next waste event for a given address_id that is on or after today's date.
        """
        cur = self._get_cursor()

        # Now we can query by address_id directly
        cur.execute(
             """
            SELECT * FROM waste_events
            WHERE address_id = ? AND date >= ?
            ORDER BY date ASC
            LIMIT 1
            """,
            (address_id, today_date),
        )
        row = cur.fetchone()
        return dict(row) if row else None
