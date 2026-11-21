import os

# Use a separate throwaway database for tests (set before the app is imported).
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest
from fastapi.testclient import TestClient

from app.auth import get_optional_user
from app.database import Base, engine
from app.main import app

client = TestClient(app)

MEGHANA = {"email": "meghana@example.com", "name": "Meghana", "picture": None}
RAVI = {"email": "ravi@example.com", "name": "Ravi", "picture": None}
signed_in = {"user": None}


def sign_in_as(user):
    """Pretend a Google sign-in happened, without calling Google."""
    signed_in["user"] = user


@pytest.fixture(autouse=True)
def fresh_state():
    """Every test starts with empty tables and nobody signed in."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_optional_user] = lambda: signed_in["user"]
    sign_in_as(None)
    yield
    app.dependency_overrides.clear()


def make_event(capacity=2, host=MEGHANA):
    sign_in_as(host)
    response = client.post(
        "/events",
        json={"title": "Python Meetup", "venue": "Mumbai", "starts_at": "2026-12-05T18:00:00", "capacity": capacity},
    )
    assert response.status_code == 201
    return response.json()


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_home_page_loads():
    response = client.get("/")
    assert response.status_code == 200
    assert "Meetup RSVP" in response.text


def test_must_sign_in_to_create_event():
    response = client.post(
        "/events", json={"title": "X", "venue": "Y", "starts_at": "2026-12-05T18:00:00", "capacity": 3}
    )
    assert response.status_code == 401


def test_must_sign_in_to_rsvp():
    event = make_event()
    sign_in_as(None)
    assert client.post(f"/events/{event['id']}/rsvp").status_code == 401


def test_host_is_recorded():
    event = make_event(capacity=5)
    assert event["host_name"] == "Meghana"
    assert event["you_are_hosting"] is True
    assert event["seats_left"] == 5


def test_rsvp_takes_a_seat_and_marks_you_going():
    event = make_event()
    sign_in_as(RAVI)
    response = client.post(f"/events/{event['id']}/rsvp")
    assert response.status_code == 201
    assert response.json()["seats_left"] == 1
    assert response.json()["you_are_going"] is True


def test_cannot_rsvp_twice():
    event = make_event()
    sign_in_as(RAVI)
    client.post(f"/events/{event['id']}/rsvp")
    response = client.post(f"/events/{event['id']}/rsvp")
    assert response.status_code == 409
    assert "already" in response.json()["detail"]


def test_cannot_rsvp_when_event_is_full():
    event = make_event(capacity=1)
    sign_in_as(RAVI)
    client.post(f"/events/{event['id']}/rsvp")
    sign_in_as(MEGHANA)
    response = client.post(f"/events/{event['id']}/rsvp")
    assert response.status_code == 409
    assert response.json()["detail"] == "Event is full"


def test_attendee_list_shows_names_but_never_emails():
    event = make_event()
    sign_in_as(RAVI)
    client.post(f"/events/{event['id']}/rsvp")
    sign_in_as(None)
    people = client.get(f"/events/{event['id']}/attendees").json()
    assert people == [{"name": "Ravi"}]


def test_unknown_event_returns_404():
    assert client.get("/events/999").status_code == 404


@pytest.mark.parametrize("bad", [{"capacity": 0}, {"title": ""}, {"starts_at": "not-a-date"}])
def test_invalid_event_is_rejected(bad):
    sign_in_as(MEGHANA)
    payload = {"title": "X", "venue": "Y", "starts_at": "2026-12-05T18:00:00", "capacity": 3, **bad}
    assert client.post("/events", json=payload).status_code == 422


def test_login_explains_when_google_is_not_configured(monkeypatch):
    monkeypatch.setattr("app.auth.GOOGLE_CONFIGURED", False)
    response = client.get("/login", follow_redirects=False)
    assert response.status_code == 503
    assert "GOOGLE_CLIENT_ID" in response.json()["detail"]


def test_logout_clears_session():
    assert client.post("/logout").json() == {"signed_out": True}