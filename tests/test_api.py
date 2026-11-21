import os

# Use a separate throwaway database for tests (set before the app is imported).
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_database():
    """Start every test with empty tables."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def make_event(capacity=2):
    response = client.post(
        "/events",
        json={"title": "Python Meetup", "venue": "Mumbai", "starts_at": "2026-12-05T18:00:00", "capacity": capacity},
    )
    assert response.status_code == 201
    return response.json()


def rsvp(event_id, name, email):
    return client.post(f"/events/{event_id}/rsvp", json={"name": name, "email": email})


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_home_page_loads():
    response = client.get("/")
    assert response.status_code == 200
    assert "Meetup RSVP" in response.text


def test_create_event_starts_with_all_seats_open():
    event = make_event(capacity=5)
    assert event["seats_left"] == 5


def test_rsvp_takes_a_seat():
    event = make_event()
    assert rsvp(event["id"], "Meghana", "meghana@example.com").status_code == 201
    assert client.get(f"/events/{event['id']}").json()["seats_left"] == 1


def test_same_email_cannot_rsvp_twice_even_with_different_case():
    event = make_event()
    rsvp(event["id"], "Meghana", "meghana@example.com")
    response = rsvp(event["id"], "Meghana", "MEGHANA@example.com")
    assert response.status_code == 409
    assert "already" in response.json()["detail"]


def test_cannot_rsvp_when_event_is_full():
    event = make_event(capacity=1)
    rsvp(event["id"], "A", "a@example.com")
    response = rsvp(event["id"], "B", "b@example.com")
    assert response.status_code == 409
    assert response.json()["detail"] == "Event is full"


def test_unknown_event_returns_404():
    assert client.get("/events/999").status_code == 404


@pytest.mark.parametrize("bad", [{"capacity": 0}, {"title": ""}, {"starts_at": "not-a-date"}])
def test_invalid_event_is_rejected(bad):
    payload = {"title": "X", "venue": "Y", "starts_at": "2026-12-05T18:00:00", "capacity": 3, **bad}
    assert client.post("/events", json=payload).status_code == 422


def test_invalid_email_is_rejected():
    event = make_event()
    assert rsvp(event["id"], "A", "not-an-email").status_code == 422