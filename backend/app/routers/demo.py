from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Payment, RecoveryCase, Execution, AuditLog
from ..services.synthetic_data import generate_synthetic_payments
from ..services.decision_engine import diagnose_and_recommend

router = APIRouter()

@router.post("/seed")
def seed_database(db: Session = Depends(get_db)):
    db.query(AuditLog).delete()
    db.query(Execution).delete()
    db.query(RecoveryCase).delete()
    db.query(Payment).delete()
    db.commit()
    
    count = generate_synthetic_payments(db, 100)
    
    payments = db.query(Payment).all()
    for p in payments:
        diagnosis, action = diagnose_and_recommend(db, p)
        case = RecoveryCase(
            payment_id=p.id,
            diagnosis=diagnosis,
            recommended_action=action
        )
        db.add(case)
    db.commit()
    
    return {"message": f"Successfully seeded {count} payments and generated recovery cases."}

@router.post("/reset")
def reset_database(db: Session = Depends(get_db)):
    db.query(AuditLog).delete()
    db.query(Execution).delete()
    db.query(RecoveryCase).delete()
    db.query(Payment).delete()
    db.commit()
    return {"message": "Database reset complete."}
