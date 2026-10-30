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

raw_db_url = settings.database_url
# Render and Heroku provision PostgreSQL connection strings starting with postgres://
# SQLAlchemy 1.4+ and 2.0+ require postgresql://
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

_connect_args = {"check_same_thread": False} if raw_db_url.startswith("sqlite") else {}

engine = create_engine(raw_db_url, connect_args=_connect_args, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
