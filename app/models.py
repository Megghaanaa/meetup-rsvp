from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    venue: Mapped[str] = mapped_column(String(200))
    starts_at: Mapped[datetime]
    capacity: Mapped[int]

    rsvps: Mapped[list["Rsvp"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class Rsvp(Base):
    __tablename__ = "rsvps"
    # The database itself refuses a second RSVP with the same email for one event.
    __table_args__ = (UniqueConstraint("event_id", "email", name="one_rsvp_per_email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254))

    event: Mapped[Event] = relationship(back_populates="rsvps")
