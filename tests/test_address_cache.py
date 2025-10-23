import sqlite3
import pytest
from unittest.mock import patch

from schedule_parser.address_cache import get_address_id

@pytest.fixture
def temp_db(tmp_path):
    """Fixture to create a temporary database for testing."""
    db_path = tmp_path / "test_address.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE addresses (
            address TEXT PRIMARY KEY,
            address_id INTEGER NOT NULL
        )
    """)
    cursor.execute("INSERT INTO addresses VALUES (?, ?)", ("chemnitzer straße 42", 54321))
    cursor.execute("INSERT INTO addresses VALUES (?, ?)", ("test straße 1", 12345))
    conn.commit()
    conn.close()

    yield db_path

def test_get_address_id_success(temp_db):
    """Test that the correct ID is returned for a valid address."""
    address_id = get_address_id("Chemnitzer Straße 42", db_path=temp_db)
    assert address_id == 54321

def test_get_address_id_not_found(temp_db):
    """Test that a ValueError is raised for an address that is not found."""
    with pytest.raises(ValueError, match="Address not found: Nonexistent Straße 99"):
        get_address_id("Nonexistent Straße 99", db_path=temp_db)

def test_get_address_id_case_insensitive(temp_db):
    """Test that address matching is case-insensitive."""
    address_id = get_address_id("chemnitzer straße 42", db_path=temp_db)
    assert address_id == 54321

def test_get_address_id_db_not_found():
    """Test that FileNotFoundError is raised if the DB file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        get_address_id("any address", db_path="non_existent_db.db")
