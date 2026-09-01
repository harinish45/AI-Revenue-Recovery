from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings


def resolve_connect_args(database_url: str) -> dict:
    """check_same_thread is a SQLite-specific DBAPI argument -- passing it
    unconditionally means switching DATABASE_URL to Postgres/MySQL wouldn't
    just be a config change, it would crash at startup with a TypeError
    from the driver's connect(), silently contradicting the documented
    "DATABASE_URL is the only thing that changes" migration path."""
    return {"check_same_thread": False} if database_url.startswith("sqlite") else {}


engine = create_engine(
    settings.DATABASE_URL,
    connect_args=resolve_connect_args(settings.DATABASE_URL),
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
