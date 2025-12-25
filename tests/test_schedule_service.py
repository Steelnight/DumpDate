"""
Unit tests for the ScheduleService.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
import requests

from schedule_parser.exceptions import DownloadError, ParsingError
from schedule_parser.services.schedule_service import ScheduleService

# A sample valid ICS file content for mocking
SAMPLE_ICS_CONTENT = """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:123@test.com
DTSTART;VALUE=DATE:20231027
SUMMARY:Rest-Tonne
LOCATION:Test Location
DESCRIPTION:Abholung durch Saubermann AG
END:VEVENT
END:VCALENDAR
"""

EMPTY_ICS_CONTENT = """
BEGIN:VCALENDAR
END:VCALENDAR
"""

INVALID_EVENT_ICS_CONTENT = """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:123@test.com
SUMMARY:Rest-Tonne
END:VEVENT
END:VCALENDAR
"""


@patch("schedule_parser.services.schedule_service.requests.get")
def test_download_and_parse_success(mock_requests_get):
    """
    Tests the successful download and parsing of a schedule.
    """
    # Arrange
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = SAMPLE_ICS_CONTENT
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    service = ScheduleService()

    # Act
    events = service.download_and_parse_schedule(
        standort_id=1,
        start_date=date(2023, 1, 1),
        end_date=date(2023, 12, 31),
        original_address="Test Straße 1",
    )

    # Assert
    assert len(events) == 1
    assert events[0].uid == "123@test.com"
    assert events[0].waste_type == "Rest-Tonne"
    assert events[0].original_address == "Test Straße 1"
    mock_requests_get.assert_called_once()


@patch("schedule_parser.services.schedule_service.requests.get")
def test_download_failure_raises_download_error(mock_requests_get):
    """
    Tests that a DownloadError is raised after retries on network failure.
    """
    # Arrange
    mock_requests_get.side_effect = requests.exceptions.RequestException(
        "Network error"
    )
    # Make retries fast for the test
    service = ScheduleService(max_retries=2, retry_delay=0.1)

    # Act & Assert
    with pytest.raises(DownloadError, match="Network error"):
        service.download_and_parse_schedule(
            standort_id=1,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            original_address="Test Straße 1",
        )
    assert mock_requests_get.call_count == 2


@patch("schedule_parser.services.schedule_service.requests.get")
def test_download_http_error_raises_download_error(mock_requests_get):
    """
    Tests that a DownloadError is raised after retries on HTTP error.
    """
    # Arrange
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "Not Found"
    )
    mock_requests_get.return_value = mock_response
    # Make retries fast for the test
    service = ScheduleService(max_retries=2, retry_delay=0.1)

    # Act & Assert
    with pytest.raises(DownloadError):
        service.download_and_parse_schedule(
            standort_id=1,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            original_address="Test Straße 1",
        )
    assert mock_requests_get.call_count == 2


@patch("schedule_parser.services.schedule_service.requests.get")
def test_invalid_content_raises_download_error(mock_requests_get):
    """
    Tests that a DownloadError is raised for content that is not an ICS file.
    """
    # Arrange
    mock_response = MagicMock()
    mock_response.text = "INVALID ICS CONTENT"
    mock_requests_get.return_value = mock_response

    service = ScheduleService()

    # Act & Assert
    with pytest.raises(DownloadError):
        service.download_and_parse_schedule(
            standort_id=1,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            original_address="Test Straße 1",
        )


@patch("schedule_parser.services.schedule_service.requests.get")
def test_malformed_ical_raises_parsing_error(mock_requests_get):
    """
    Tests that a ParsingError is raised for malformed ICS content.
    """
    # Arrange
    mock_response = MagicMock()
    # Passes the BEGIN:VCALENDAR check but fails parsing
    mock_response.text = "BEGIN:VCALENDAR\nINVALID LINE"
    mock_requests_get.return_value = mock_response

    service = ScheduleService()

    # Act & Assert
    with pytest.raises(ParsingError):
        service.download_and_parse_schedule(
            standort_id=1,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            original_address="Test Straße 1",
        )


@patch("schedule_parser.services.schedule_service.requests.get")
def test_empty_ics_file(mock_requests_get):
    """
    Tests that an empty list is returned for a valid but empty ICS file.
    """
    # Arrange
    mock_response = MagicMock()
    mock_response.text = EMPTY_ICS_CONTENT
    mock_requests_get.return_value = mock_response

    service = ScheduleService()

    # Act
    events = service.download_and_parse_schedule(
        standort_id=1,
        start_date=date(2023, 1, 1),
        end_date=date(2023, 12, 31),
        original_address="Test Straße 1",
    )

    # Assert
    assert len(events) == 0


@patch("schedule_parser.services.schedule_service.requests.get")
def test_ics_file_with_invalid_event(mock_requests_get):
    """
    Tests that an event is skipped if it is missing the DTSTART field.
    """
    # Arrange
    mock_response = MagicMock()
    mock_response.text = INVALID_EVENT_ICS_CONTENT
    mock_requests_get.return_value = mock_response

    service = ScheduleService()

    # Act
    events = service.download_and_parse_schedule(
        standort_id=1,
        start_date=date(2023, 1, 1),
        end_date=date(2023, 12, 31),
        original_address="Test Straße 1",
    )

    # Assert
    assert len(events) == 0
