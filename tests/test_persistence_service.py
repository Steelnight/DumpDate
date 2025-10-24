"""
Unit tests for the PersistenceService.
"""
import pytest
import sqlite3

from schedule_parser.services.persistence_service import PersistenceService
from schedule_parser.models import WasteEvent

@pytest.fixture
def temp_main_db(tmp_path):
    """Creates a temporary main database for testing."""
    db_path = tmp_path / "test_waste_schedule.db"
    service = PersistenceService(db_path=str(db_path))
    with service as p:
        p.init_db()
    return str(db_path)

def test_init_db_creates_tables(temp_main_db):
    """Tests that all tables are created by init_db."""
    conn = sqlite3.connect(temp_main_db)
    cur = conn.cursor()
    tables = [row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    conn.close()
    assert "waste_events" in tables
    assert "subscriptions" in tables
    assert "logs" in tables
    assert "notification_logs" in tables

def test_upsert_event_insert(temp_main_db):
    """Tests inserting a new event."""
    service = PersistenceService(db_path=temp_main_db)
    event = WasteEvent("uid1", "2023-10-27", "loc", "Rest", "", "", "addr")

    with service as p:
        p.upsert_event(event)

    conn = sqlite3.connect(temp_main_db)
    cur = conn.cursor()
    cur.execute("SELECT * FROM waste_events WHERE uid = 'uid1'")
    assert cur.fetchone() is not None
    conn.close()

def test_upsert_event_update(temp_main_db):
    """Tests updating an existing event."""
    service = PersistenceService(db_path=temp_main_db)
    event1 = WasteEvent("uid1", "2023-10-27", "loc", "Rest", "", "", "addr1")
    event2 = WasteEvent("uid1", "2023-10-28", "loc", "Bio", "", "", "addr2") # Same UID, different data

    with service as p:
        p.upsert_event(event1)
        p.upsert_event(event2)

    conn = sqlite3.connect(temp_main_db)
    cur = conn.cursor()
    cur.execute("SELECT waste_type, original_address FROM waste_events WHERE uid = 'uid1'")
    row = cur.fetchone()
    conn.close()
    assert row[0] == "Bio"
    assert row[1] == "addr2"

def test_subscription_workflow(temp_main_db):
    """Tests the full subscription and notification log workflow."""
    service = PersistenceService(db_path=temp_main_db)

    with service as p:
        # Create
        p.create_subscription(chat_id=123, address_id=456, notification_time="evening")
        subs = p.get_subscriptions_by_chat_id(123)
        assert len(subs) == 1
        sub_id = subs[0]["id"]

        # Deactivate (soft delete)
        p.deactivate_subscription(sub_id)
        subs = p.get_subscriptions_by_chat_id(123)
        assert len(subs) == 0

        # Reactivate
        p.reactivate_subscription(sub_id, "morning")
        subs = p.get_subscriptions_by_chat_id(123)
        assert len(subs) == 1
        assert subs[0]["notification_time"] == "morning"

        # Notification logging
        log_id = p.create_notification_log(sub_id, "pending")
        assert log_id is not None
        p.update_notification_log_status(log_id, "success")

        conn = sqlite3.connect(temp_main_db)
        cur = conn.cursor()
        cur.execute("SELECT status FROM notification_logs WHERE id = ?", (log_id,))
        assert cur.fetchone()[0] == "success"
        conn.close()
