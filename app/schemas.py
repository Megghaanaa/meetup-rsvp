from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    venue: str = Field(min_length=1, max_length=200)
    starts_at: datetime
    capacity: int = Field(gt=0, le=10000)


class EventOut(EventCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    seats_left: int


class RsvpCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=254)


class RsvpOut(RsvpCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
