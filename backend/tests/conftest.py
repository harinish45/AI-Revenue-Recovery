"""
conftest.py — Shared pytest fixtures
--------------------------------------
Key design:
  - We override `app.database.engine` with a fresh in-memory SQLite engine
    before any test. This ensures `Base.metadata.create_all` in lifespan
    creates tables on the test engine, not the production one.
  - StaticPool is required so all connections share the same in-memory DB.
  - Tables are created/dropped per test function for full isolation.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

SQLALCHEMY_DATABASE_URL = "sqlite://"


@pytest.fixture(scope="function")
def db():
    """Provide a clean database session with tables created on test engine."""
    import app.database as db_module
    from app.database import Base

    # Create a per-test in-memory engine
    test_engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Patch the global engine so lifespan and get_db both use it
    original_engine = db_module.engine
    db_module.engine = test_engine

    # Also patch SessionLocal
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    original_session_local = db_module.SessionLocal
    db_module.SessionLocal = TestingSessionLocal

    # Create all tables on the test engine
    Base.metadata.create_all(bind=test_engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)
        # Restore originals
        db_module.engine = original_engine
        db_module.SessionLocal = original_session_local


@pytest.fixture(scope="function")
def client(db):
    """Provide a test client using the test database."""
    from app.main import app
    from app.database import get_db

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
