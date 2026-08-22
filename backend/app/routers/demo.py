from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db, engine, Base
from app.models import Payment, RecoveryCase, AuditLog
from app.services.synthetic_data import generate_synthetic_data

router = APIRouter()

@router.post("/seed")
def seed_data(db: Session = Depends(get_db)):
    db.query(AuditLog).delete()
    db.query(RecoveryCase).delete()
    db.query(Payment).delete()
    db.commit()
    
    count = generate_synthetic_data(db, 100)
    return {"message": f"Seeded {count} synthetic payment records."}

@router.post("/reset")
def reset_data(db: Session = Depends(get_db)):
    db.query(AuditLog).delete()
    db.query(RecoveryCase).delete()
    db.query(Payment).delete()
    db.commit()
    return {"message": "Database reset successfully."}
