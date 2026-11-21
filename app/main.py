import os
import secrets
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app import models, schemas
from app.auth import get_optional_user, get_user
from app.auth import router as auth_router
from app.database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Meetup RSVP")
app.add_middleware(
    SessionMiddleware,
    # A signed cookie remembers who is signed in. Set SESSION_SECRET in production.
    secret_key=os.getenv("SESSION_SECRET") or secrets.token_urlsafe(32),
    same_site="lax",
    https_only=os.getenv("HTTPS_ONLY", "false").lower() == "true",
)
app.include_router(auth_router)

STATIC_DIR = Path(__file__).parent / "static"


def to_event_out(event: models.Event, user: Optional[dict]) -> schemas.EventOut:
    email = user["email"] if user else None
    return schemas.EventOut(
        id=event.id,
        title=event.title,
        venue=event.venue,
        starts_at=event.starts_at,
        capacity=event.capacity,
        seats_left=event.capacity - len(event.rsvps),
        host_name=event.host_name,
        you_are_going=any(r.email == email for r in event.rsvps),
        you_are_hosting=event.host_email == email,
    )


def get_event_or_404(event_id: int, db: Session) -> models.Event:
    event = db.get(models.Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/events", response_model=schemas.EventOut, status_code=201)
def create_event(
    payload: schemas.EventCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_user),
):
    event = models.Event(**payload.model_dump(), host_email=user["email"], host_name=user["name"])
    db.add(event)
    db.commit()
    db.refresh(event)
    return to_event_out(event, user)


@app.get("/events", response_model=list[schemas.EventOut])
def list_events(db: Session = Depends(get_db), user: Optional[dict] = Depends(get_optional_user)):
    events = db.scalars(select(models.Event).order_by(models.Event.starts_at)).all()
    return [to_event_out(e, user) for e in events]


@app.get("/events/{event_id}", response_model=schemas.EventOut)
def get_event(event_id: int, db: Session = Depends(get_db), user: Optional[dict] = Depends(get_optional_user)):
    return to_event_out(get_event_or_404(event_id, db), user)


@app.post("/events/{event_id}/rsvp", response_model=schemas.EventOut, status_code=201)
def rsvp(event_id: int, db: Session = Depends(get_db), user: dict = Depends(get_user)):
    event = get_event_or_404(event_id, db)
    if len(event.rsvps) >= event.capacity:
        raise HTTPException(status_code=409, detail="Event is full")

    # Name and email come from the Google account, so nobody can RSVP as someone else.
    db.add(models.Rsvp(event_id=event.id, name=user["name"], email=user["email"]))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="You have already RSVPed to this event")
    db.refresh(event)
    return to_event_out(event, user)


@app.get("/events/{event_id}/attendees", response_model=list[schemas.AttendeeOut])
def attendees(event_id: int, db: Session = Depends(get_db)):
    return [schemas.AttendeeOut(name=r.name) for r in get_event_or_404(event_id, db).rsvps]