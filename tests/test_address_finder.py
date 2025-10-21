from unittest.mock import Mock, patch

import pytest

from schedule_parser.address_finder import get_address_id


@pytest.fixture
def mock_requests_get():
    """Fixture to mock requests.get."""
    with patch("requests.get") as mock_get:
        yield mock_get


def test_get_address_id_success(mock_requests_get):
    """Test that the correct ID is returned for a valid address."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "features": [
            {"properties": {"id": 12345, "adresse": "Test Straße 1"}},
            {"properties": {"id": 54321, "adresse": "Chemnitzer Straße 42"}},
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    address_id = get_address_id("Chemnitzer Straße 42")
    assert address_id == 54321


def test_get_address_id_not_found(mock_requests_get):
    """Test that a ValueError is raised for an address that is not found."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "features": [{"properties": {"id": 12345, "adresse": "Test Straße 1"}}]
    }
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    with pytest.raises(ValueError, match="Address not found: Nonexistent Straße 99"):
        get_address_id("Nonexistent Straße 99")


def test_get_address_id_case_insensitive(mock_requests_get):
    """Test that address matching is case-insensitive."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "features": [{"properties": {"id": 54321, "adresse": "Chemnitzer Straße 42"}}]
    }
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    address_id = get_address_id("chemnitzer straße 42")
    assert address_id == 54321
