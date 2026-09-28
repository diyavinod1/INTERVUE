from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db.database import Base, SessionLocal, engine


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Create tables if they don't exist. In a real production deployment you'd
    replace this with Alembic migrations; for this project's scope,
    create_all is explicit, transparent, and easy for a reader to follow.
    """
    from app.models import (  # noqa: F401  (import so metadata is populated)
        answer,
        candidate,
        evaluation,
        interview,
        question,
        report,
    )

    Base.metadata.create_all(bind=engine)
