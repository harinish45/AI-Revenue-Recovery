"""
metrics_service.py
------------------
Dashboard metrics computation.

Revenue at risk formula:
  total_at_risk = SUM(amount) WHERE status IN ('failed', 'abandoned')
  (NOT all payments — only genuinely at-risk ones)

Recovery rate formula:
  recovery_rate = (total_recovered / total_at_risk) * 100
  (returns 0.0 if total_at_risk == 0 to avoid ZeroDivisionError)
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import Payment, RecoveryCase, Execution


def get_metrics(db: Session) -> dict:
    """
    Compute all dashboard metrics from live database state.

    Returns:
        dict matching DashboardSummary schema
    """
    # Total payments in the system
    total_payments: int = db.query(Payment).count()

    # Revenue at risk = only failed/abandoned payments
    total_at_risk: float = (
        db.query(func.sum(Payment.amount))
        .filter(Payment.status.in_(["failed", "abandoned"]))
        .scalar()
        or 0.0
    )

    # Total recovered = sum of all successful execution amounts
    total_recovered: float = (
        db.query(func.sum(Execution.amount_recovered))
        .scalar()
        or 0.0
    )

    # Recovery rate — safe zero denominator
    recovery_rate: float = (
        (total_recovered / total_at_risk * 100) if total_at_risk > 0 else 0.0
    )

    # Case status counts
    open_cases: int = (
        db.query(RecoveryCase).filter(RecoveryCase.status == "OPEN").count()
    )
    escalated_cases: int = (
        db.query(RecoveryCase)
        .filter(RecoveryCase.status.in_(["ESCALATED", "NEEDS_HUMAN_REVIEW"]))
        .count()
    )

    # Execution stats
    all_executions = db.query(Execution).all()
    recovery_attempts: int = len(all_executions)
    successful_recoveries: int = sum(
        1 for e in all_executions if e.amount_recovered > 0
    )
    failed_recoveries: int = recovery_attempts - successful_recoveries

    return {
        "total_payments": total_payments,
        "total_at_risk": round(total_at_risk, 2),
        "total_recovered": round(total_recovered, 2),
        "recovery_rate_percent": round(recovery_rate, 2),
        "open_cases": open_cases,
        "escalated_cases": escalated_cases,
        "recovery_attempts": recovery_attempts,
        "successful_recoveries": successful_recoveries,
        "failed_recoveries": failed_recoveries,
    }
