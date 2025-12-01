"""
Unit tests for the AddressService.
"""

import sqlite3

import pytest

from schedule_parser.services.address_service import AddressService


@pytest.fixture
def temp_address_db(tmp_path):
    """Creates a temporary address database for testing."""
    db_path = tmp_path / "test_address_lookup.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE addresses (address_id INTEGER, address TEXT)")
    cur.execute("INSERT INTO addresses VALUES (1, 'test straße 1')")
    cur.execute("INSERT INTO addresses VALUES (2, 'musterweg 2')")
    cur.execute("INSERT INTO addresses VALUES (3, 'beispiel-allee 3')")
    conn.commit()
    conn.close()
    return str(db_path)


def test_get_address_id_success(temp_address_db):
    """Tests finding an address ID with an exact match."""
    service = AddressService(db_path=temp_address_db)
    address_id = service.get_address_id("test straße 1")
    assert address_id == 1


def test_get_address_id_not_found_raises_error(temp_address_db):
    """Tests that a ValueError is raised for a non-existent address."""
    service = AddressService(db_path=temp_address_db)
    with pytest.raises(ValueError, match="Address not found"):
        service.get_address_id("nicht-existent-straße")


def test_find_address_matches_exact(temp_address_db):
    """Tests finding an exact match with find_address_matches."""
    service = AddressService(db_path=temp_address_db)
    matches = service.find_address_matches("musterweg 2")
    assert len(matches) == 1
    assert matches[0] == ("musterweg 2", 2)


def test_find_address_matches_fuzzy(temp_address_db):
    """Tests finding a fuzzy match."""
    service = AddressService(db_path=temp_address_db)
    # "beispiel" is close to "beispiel-allee"
    matches = service.find_address_matches("beispiel")
    assert len(matches) > 0
    assert matches[0][0] == "beispiel-allee 3"


def test_find_address_matches_no_match(temp_address_db):
    """Tests that an empty list is returned when no match is found."""
    service = AddressService(db_path=temp_address_db)
    matches = service.find_address_matches("xyz")
    assert len(matches) == 0


def test_address_service_db_not_found():
    """Tests that a FileNotFoundError is raised if the database does not exist."""
    service = AddressService(db_path="/non/existent/path.db")
    with pytest.raises(FileNotFoundError):
        service.get_address_id("any address")
