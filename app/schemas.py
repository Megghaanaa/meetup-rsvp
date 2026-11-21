from datetime import datetime

from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    venue: str = Field(min_length=1, max_length=200)
    starts_at: datetime
    capacity: int = Field(gt=0, le=10000)


class EventOut(EventCreate):
    id: int
    seats_left: int
    host_name: str
    you_are_going: bool
    you_are_hosting: bool


class AttendeeOut(BaseModel):
    # Names only: attendee emails are never shown publicly.
    name: str