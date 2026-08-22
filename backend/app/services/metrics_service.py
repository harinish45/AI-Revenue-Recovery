from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Payment, RecoveryCase, RecoveryStatus, PaymentStatus
from app.services.risk_calculator import calculate_revenue_at_risk, calculate_recovered_amount

def get_dashboard_metrics(db: Session):
    total_at_risk = calculate_revenue_at_risk(db)
    total_recovered = calculate_recovered_amount(db)
    
    open_cases = db.query(RecoveryCase).filter(
        RecoveryCase.status.in_([RecoveryStatus.OPEN, RecoveryStatus.NUDGED])
    ).count()
    
    escalated_cases = db.query(RecoveryCase).filter(
        RecoveryCase.status == RecoveryStatus.ESCALATED
    ).count()
    
    recovery_rate = (total_recovered / (total_at_risk + total_recovered)) * 100 if (total_at_risk + total_recovered) > 0 else 0.0
    
    return {
        "total_at_risk": total_at_risk,
        "total_recovered": total_recovered,
        "open_cases": open_cases,
        "escalated_cases": escalated_cases,
        "recovery_rate": round(recovery_rate, 2)
    }
