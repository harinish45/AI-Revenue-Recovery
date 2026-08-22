from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import Payment, RecoveryCase, Execution

def get_metrics(db: Session):
    total_transactions = db.query(Payment).count()
    failed_payments = db.query(Payment).filter(Payment.status == "failed").count()
    
    total_revenue = db.query(func.sum(Payment.amount)).filter(Payment.status == "success").scalar() or 0.0
    revenue_at_risk = db.query(func.sum(RecoveryCase.amount_at_risk)).filter(RecoveryCase.recovery_status == "pending").scalar() or 0.0
    recovered_amount = db.query(func.sum(RecoveryCase.recovered_amount)).scalar() or 0.0
    
    recovery_attempts = db.query(Execution).count()
    successful_recoveries = db.query(RecoveryCase).filter(RecoveryCase.recovery_status == "recovered").count()
    failed_recoveries = db.query(RecoveryCase).filter(RecoveryCase.recovery_status == "failed").count()
    escalated_cases = db.query(RecoveryCase).filter(RecoveryCase.recovery_status.in_(["needs_human_review", "blocked"])).count()
    
    recovery_rate = (successful_recoveries / (successful_recoveries + failed_recoveries + escalated_cases) * 100) if (successful_recoveries + failed_recoveries + escalated_cases) > 0 else 0.0

    return {
        "total_revenue": total_revenue,
        "revenue_at_risk": revenue_at_risk,
        "recovered_amount": recovered_amount,
        "recovery_rate": round(recovery_rate, 1),
        "total_transactions": total_transactions,
        "failed_payments": failed_payments,
        "recovery_attempts": recovery_attempts,
        "successful_recoveries": successful_recoveries,
        "failed_recoveries": failed_recoveries,
        "escalated_cases": escalated_cases
    }
