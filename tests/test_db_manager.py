import sqlite3

from schedule_parser.db_manager import init_db, upsert_event
from schedule_parser.models import WasteEvent


def test_insert_and_dedup(tmp_path):
    db_file = tmp_path / "test.db"
    init_db(db_path=db_file)
    e1 = WasteEvent(
        "uid1",
        "2024-05-15",
        "Musterweg 123",
        "Bio-Tonne",
        "Sauber- & Entsorgungs-AG",
        "0123-456789",
    )
    upsert_event(e1, db_path=db_file)
    e2 = WasteEvent(
        "uid2",
        "2024-05-15",
        "Musterweg 123",
        "Bio-Tonne",
        "Sauber- & Entsorgungs-AG",
        "0123-456789",
    )
    upsert_event(e2, db_path=db_file)
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM waste_events")
    count = cur.fetchone()[0]
    conn.close()
    assert count == 1  # identical hash, different UID should not insert


def test_insert_and_update(tmp_path):
    db_file = tmp_path / "test.db"
    init_db(db_path=db_file)
    e1 = WasteEvent(
        "uid1",
        "2024-05-15",
        "Musterweg 123",
        "Bio-Tonne",
        "Sauber- & Entsorgungs-AG",
        "0123-456789",
    )
    upsert_event(e1, db_path=db_file)

    e1_updated = WasteEvent(
        "uid1", "2024-05-15", "Musterweg 123", "Bio-Tonne", "UPDATED", "0123-456789"
    )
    upsert_event(e1_updated, db_path=db_file)

    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("SELECT contact_name, hash FROM waste_events WHERE uid = 'uid1'")
    row = cur.fetchone()
    conn.close()

    assert row[0] == "UPDATED"
    assert row[1] == e1_updated.compute_hash()
