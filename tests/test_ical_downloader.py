import pytest
import requests
from unittest.mock import patch, Mock
from datetime import date
import os
from schedule_parser.ical_downloader import download_ical_file

@pytest.fixture
def mock_requests_get():
    """Fixture to mock requests.get."""
    with patch('requests.get') as mock_get:
        yield mock_get

def test_download_ical_file_success(mock_requests_get):
    """Test that the iCal file is downloaded and a path is returned."""
    mock_response = Mock()
    mock_response.text = "BEGIN:VCALENDAR..."
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    standort_id = 54321
    start_date = date(2026, 1, 1)
    end_date = date(2026, 12, 31)

    file_path = download_ical_file(standort_id, start_date, end_date)

    assert file_path is not None
    assert os.path.exists(file_path)
    with open(file_path, 'r') as f:
        assert f.read() == "BEGIN:VCALENDAR..."

    # Clean up the created temp file
    if file_path:
        os.remove(file_path)

def test_download_ical_file_http_error(mock_requests_get):
    """Test that None is returned on an HTTP error."""
    mock_requests_get.side_effect = requests.exceptions.HTTPError("404 Not Found")

    standort_id = 12345
    start_date = date(2026, 1, 1)
    end_date = date(2026, 12, 31)

    file_path = download_ical_file(standort_id, start_date, end_date)
    assert file_path is None
