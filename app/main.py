from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Meetup RSVP")
STATIC_DIR = Path(__file__).parent / "static"


def to_event_out(event: models.Event) -> schemas.EventOut:
    return schemas.EventOut(
        id=event.id,
        title=event.title,
        venue=event.venue,
        starts_at=event.starts_at,
        capacity=event.capacity,
        seats_left=event.capacity - len(event.rsvps),
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
def create_event(payload: schemas.EventCreate, db: Session = Depends(get_db)):
    event = models.Event(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return to_event_out(event)


@app.get("/events", response_model=list[schemas.EventOut])
def list_events(db: Session = Depends(get_db)):
    events = db.scalars(select(models.Event).order_by(models.Event.starts_at)).all()
    return [to_event_out(e) for e in events]


@app.get("/events/{event_id}", response_model=schemas.EventOut)
def get_event(event_id: int, db: Session = Depends(get_db)):
    return to_event_out(get_event_or_404(event_id, db))


@app.post("/events/{event_id}/rsvp", response_model=schemas.RsvpOut, status_code=201)
def rsvp(event_id: int, payload: schemas.RsvpCreate, db: Session = Depends(get_db)):
    event = get_event_or_404(event_id, db)
    if len(event.rsvps) >= event.capacity:
        raise HTTPException(status_code=409, detail="Event is full")

    rsvp = models.Rsvp(event_id=event.id, name=payload.name, email=payload.email.lower())
    db.add(rsvp)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="You have already RSVPed to this event")
    db.refresh(rsvp)
    return rsvp


@app.get("/events/{event_id}/attendees", response_model=list[schemas.RsvpOut])
def attendees(event_id: int, db: Session = Depends(get_db)):
    return get_event_or_404(event_id, db).rsvps
