from fastapi import Depends
from sqlalchemy.orm import Session
from .database import get_db, SessionLocal

def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
