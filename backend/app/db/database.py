"""
Database engine + session factory.

Why SQLAlchemy + a DATABASE_URL rather than the Supabase Python client
directly: Supabase *is* PostgreSQL, so talking to it with SQLAlchemy over
the standard Postgres connection string gives us real relational schema,
migrations-friendly models, and transactions - instead of treating Supabase
as a REST/JSON blob store. Point DATABASE_URL at your Supabase connection
string in production; for local development it defaults to a SQLite file so
the whole project runs with zero external services.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()


def normalize_database_url(url: str) -> str:
    """
    Ensure PostgreSQL URLs explicitly specify the installed psycopg2 driver:
    - postgres:// -> postgresql+psycopg2:// (Render / Heroku legacy scheme)
    - postgresql:// -> postgresql+psycopg2:// (Supabase / standard PostgreSQL default)
    - postgresql+psycopg:// -> postgresql+psycopg2:// (Redirect Psycopg 3 URLs to psycopg2)
    - postgresql+psycopg2:// -> retained
    - sqlite:// -> retained
    """
    if not url:
        return "sqlite:///./intervue.db"

    clean = url.strip()
    if clean.startswith("postgresql+psycopg2://"):
        return clean
    if clean.startswith("postgresql+psycopg://"):
        return clean.replace("postgresql+psycopg://", "postgresql+psycopg2://", 1)
    if clean.startswith("postgresql://"):
        return clean.replace("postgresql://", "postgresql+psycopg2://", 1)
    if clean.startswith("postgres://"):
        return clean.replace("postgres://", "postgresql+psycopg2://", 1)
    return clean


db_url = normalize_database_url(settings.database_url)
_connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

engine = create_engine(db_url, connect_args=_connect_args, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
