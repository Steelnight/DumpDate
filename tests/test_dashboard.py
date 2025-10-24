"""
Tests for the Flask dashboard application.
"""

import pytest
from dashboard.app import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_dashboard_main_route(client):
    """
    Test that the main dashboard route returns a 200 OK status.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert b"DumpDate Bot Status Dashboard" in response.data
