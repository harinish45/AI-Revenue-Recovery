from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Payment, RecoveryCase, Execution, AuditLog
from ..services.synthetic_data import generate_synthetic_payments
from ..services.decision_engine import diagnose_and_recommend
from ..services.recovery_executor import execute_recovery, arm_failure_simulation
from ..services.audit_service import log_event

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
        db.refresh(case)
        log_event(db, case.id, "LLM_DIAGNOSIS", {
            "payment_id": p.id,
            "failure_code": p.failure_code,
            "diagnosis": diagnosis,
            "recommended_action": action
        })
    db.commit()
    
    return {"message": "Successfully seeded 100 payments and generated recovery cases."}

@router.post("/reset")
def reset_database(db: Session = Depends(get_db)):
    db.query(AuditLog).delete()
    db.query(Execution).delete()
    db.query(RecoveryCase).delete()
    db.query(Payment).delete()
    db.commit()
    return {"message": "Database reset complete."}

@router.post("/recovery-batch")
def recovery_batch(db: Session = Depends(get_db)):
    cases = db.query(RecoveryCase).filter(RecoveryCase.status == "OPEN").all()
    total = len(cases)
    success = failed = escalated = 0
    recovered_amt = 0.0
    amount_at_risk = sum(c.payment.amount for c in cases)
    
    for c in cases:
        r = execute_recovery(db, c)
        st = r["status"]
        if st == "RECOVERED":
            success += 1
            recovered_amt += r.get("amount_recovered", 0)
        elif st in ["ESCALATED", "needs_human_review"]:
            escalated += 1
        else:
            failed += 1
            
    attempted = success + failed + escalated
    rate = (recovered_amt / amount_at_risk * 100) if amount_at_risk > 0 else 0.0
    
    return {
        "total_cases": total,
        "attempted": attempted,
        "successful": success,
        "failed": failed,
        "escalated": escalated,
        "amount_at_risk": amount_at_risk,
        "amount_recovered": recovered_amt,
        "recovery_rate": round(rate, 2)
    }

@router.post("/simulate-failure")
def simulate_failure():
    arm_failure_simulation()
    return {"status": "armed", "message": "Simulated gateway failure armed for the next recovery execute."}
