import sqlite3
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from schedule_parser.facade import get_schedule_for_address
from schedule_parser.models import WasteEvent


@pytest.fixture
def mock_address_finder():
    with patch("schedule_parser.facade.get_address_id") as mock_get_id:
        mock_get_id.return_value = 54321
        yield mock_get_id


@pytest.fixture
def mock_ical_downloader():
    with patch("schedule_parser.facade.download_ical_file") as mock_download:
        # Create a mock file path
        mock_download.return_value = "/tmp/mock_ical.ics"
        yield mock_download


@pytest.fixture
def mock_ics_parser():
    with patch("schedule_parser.facade.parse_ics") as mock_parse:
        mock_parse.return_value = [
            WasteEvent(
                uid="1",
                date="2026-01-01",
                location="Test",
                waste_type="Restmüll",
                contact_name="",
                contact_phone="",
                original_address="Test",
            )
        ]
        yield mock_parse


@pytest.fixture
def mock_temp_file():
    with patch("builtins.open", MagicMock()):
        with patch("os.remove") as mock_remove:
            yield mock_remove


def test_get_schedule_for_address_integration(
    tmp_path, mock_address_finder, mock_ical_downloader, mock_ics_parser, mock_temp_file
):
    """Integration test for the main facade function."""
    db_path = tmp_path / "test_waste.db"

    get_schedule_for_address(
        address="Chemnitzer Straße 42",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        db_path=str(db_path),
    )

    # Verify that the mocks were called
    mock_address_finder.assert_called_with("Chemnitzer Straße 42")
    mock_ical_downloader.assert_called_with(54321, date(2026, 1, 1), date(2026, 12, 31))
    mock_ics_parser.assert_called()

    # Verify that the data was written to the database
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM waste_events")
    rows = cur.fetchall()
    assert len(rows) == 1
    assert rows[0][1] == "1"  # UID
    conn.close()
