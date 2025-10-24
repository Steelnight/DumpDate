"""
Unit tests for the Flask Dashboard.
"""
import pytest
from unittest.mock import patch
from dashboard.app import app

# Sample data for mocking the facade's response
SAMPLE_DATA = {
    "events": [{"date": "2023-10-27", "waste_type": "Rest-Tonne", "original_address": "Test Str 1"}],
    "subscriptions": [{"chat_id": 123, "address_id": 456, "notification_time": "evening"}],
    "logs": [{"timestamp": "2023-10-26 10:00:00", "level": "INFO", "message": "Test log"}],
}

EMPTY_DATA = {
    "events": [],
    "subscriptions": [],
    "logs": [],
}

ERROR_DATA = {
    "error": "Database connection failed."
}

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_dashboard_displays_data(client):
    """
    Tests that the dashboard correctly renders data retrieved from the facade.
    """
    # Arrange
    mock_facade = patch('schedule_parser.facade.WasteManagementFacade').start()
    mock_facade.get_dashboard_data.return_value = SAMPLE_DATA
    app.config["FACADE"] = mock_facade

    # Act
    response = client.get('/')

    # Assert
    assert response.status_code == 200
    # Check for event data
    assert b"Rest-Tonne" in response.data
    assert b"Test Str 1" in response.data
    # Check for subscription data
    assert b"123" in response.data
    assert b"evening" in response.data
    # Check for log data
    assert b"Test log" in response.data
    patch.stopall()


def test_dashboard_handles_empty_data(client):
    """
    Tests that the dashboard renders correctly when the facade returns no data.
    """
    # Arrange
    mock_facade = patch('schedule_parser.facade.WasteManagementFacade').start()
    mock_facade.get_dashboard_data.return_value = EMPTY_DATA
    app.config["FACADE"] = mock_facade

    # Act
    response = client.get('/')

    # Assert
    assert response.status_code == 200
    assert b"No events found." in response.data
    assert b"No subscriptions found." in response.data
    assert b"No logs found." in response.data
    patch.stopall()


def test_dashboard_displays_error(client):
    """
    Tests that the dashboard displays an error message when the facade returns an error.
    """
    # Arrange
    mock_facade = patch('schedule_parser.facade.WasteManagementFacade').start()
    mock_facade.get_dashboard_data.return_value = ERROR_DATA
    app.config["FACADE"] = mock_facade

    # Act
    response = client.get('/')

    # Assert
    assert response.status_code == 200
    assert b"Database connection failed." in response.data
    patch.stopall()
