import pytest

from schedule_parser.ics_parser import parse_ics


@pytest.fixture
def sample_ics():
    with open("tests/sample.ics", "r") as f:
        return f.read()


def test_parse_events(sample_ics):
    events = parse_ics(sample_ics)
    assert len(events) == 7

    # Test the first event in detail
    e1 = events[0]
    assert e1.uid == "20240515T000000-event1@example.com"
    assert e1.date == "2024-05-15"
    assert e1.location == "Musterweg 123"
    assert e1.waste_type == "Bio-Tonne"
    assert e1.contact_name == "Sauber- & Entsorgungs-AG"
    assert e1.contact_phone == "0123-456789"
    assert len(e1.compute_hash()) == 64

    # Test another event to ensure variety
    e2 = events[1]
    assert e2.waste_type == "Gelbe Tonne"
    assert e2.contact_name == "Recycling-Helden GmbH"
    assert e2.contact_phone == "0800-987654"
