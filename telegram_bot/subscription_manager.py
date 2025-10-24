"""
This module manages user subscriptions in the database.
"""
import sqlite3
from typing import List, Tuple

def add_subscription(chat_id: int, address_id: int, notification_time: str, db_path: str = "waste_schedule.db") -> None:
    """Adds a new subscription or reactivates an existing one."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Check if a subscription already exists for this chat_id and address_id
    cur.execute(
        "SELECT id FROM subscriptions WHERE chat_id = ? AND address_id = ?",
        (chat_id, address_id),
    )
    result = cur.fetchone()

    if result:
        # If it exists, reactivate it and update the notification time
        subscription_id = result[0]
        cur.execute(
            "UPDATE subscriptions SET is_active = 1, notification_time = ?, last_notified = NULL WHERE id = ?",
            (notification_time, subscription_id),
        )
    else:
        # Otherwise, insert a new subscription
        cur.execute(
            "INSERT INTO subscriptions (chat_id, address_id, notification_time, last_notified) VALUES (?, ?, ?, NULL)",
            (chat_id, address_id, notification_time),
        )
    conn.commit()
    conn.close()

def get_subscriptions(chat_id: int, db_path: str = "waste_schedule.db") -> List[Tuple[int, int, str]]:
    """Retrieves all active subscriptions for a given chat_id."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, address_id, notification_time FROM subscriptions WHERE chat_id = ? AND is_active = 1",
        (chat_id,),
    )
    subscriptions = cur.fetchall()
    conn.close()
    return subscriptions


def remove_subscription(subscription_id: int, db_path: str = "waste_schedule.db") -> None:
    """Marks a subscription as inactive (soft delete)."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE subscriptions SET is_active = 0 WHERE id = ?", (subscription_id,))
    conn.commit()
    conn.close()


def get_all_subscriptions(db_path: str = "waste_schedule.db") -> List[Tuple[int, int, int, str, str]]:
    """Retrieves all active subscriptions from the database."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, chat_id, address_id, notification_time, last_notified FROM subscriptions WHERE is_active = 1"
    )
    subscriptions = cur.fetchall()
    conn.close()
    return subscriptions

def update_last_notified(subscription_id: int, notification_date: str, db_path: str = "waste_schedule.db") -> None:
    """Updates the last_notified date for a subscription."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE subscriptions SET last_notified = ? WHERE id = ?", (notification_date, subscription_id))
    conn.commit()
    conn.close()
