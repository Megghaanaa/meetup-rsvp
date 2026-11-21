import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# SQLite file locally; later Docker will set DATABASE_URL to PostgreSQL.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./meetup.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """Give each request its own database session and always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
