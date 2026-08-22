from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import Payment, RecoveryCase, Execution

def get_metrics(db: Session):
    total_payments = db.query(Payment).count()
    
    total_at_risk = db.query(func.sum(Payment.amount)).filter(
        Payment.status.in_(["failed", "abandoned"])
    ).scalar() or 0.0
    
    total_recovered = db.query(func.sum(Execution.amount_recovered)).scalar() or 0.0
    recovery_rate = (total_recovered / total_at_risk * 100) if total_at_risk > 0 else 0.0
    open_cases = db.query(RecoveryCase).filter(RecoveryCase.status == "OPEN").count()
    escalated_cases = db.query(RecoveryCase).filter(RecoveryCase.status == "ESCALATED").count()
    
    return {
        "total_payments": total_payments,
        "total_at_risk": total_at_risk,
        "total_recovered": total_recovered,
        "recovery_rate_percent": round(recovery_rate, 2),
        "open_cases": open_cases,
        "escalated_cases": escalated_cases
    }
