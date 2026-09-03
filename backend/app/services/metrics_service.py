"""Dashboard summary metrics, short-TTL cached so bursts of reads don't
recompute aggregates on every request while still reflecting mutations
within a few seconds (see ``invalidate_metrics_cache``, called by every
mutation path)."""

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Execution, Payment, RecoveryCase
from ..utils.cache import TTLCache

_cache = TTLCache(ttl_seconds=3)


def get_metrics(db: Session) -> dict:
    return _cache.get_or_set("dashboard_summary", lambda: _compute_metrics(db))


def invalidate_metrics_cache() -> None:
    """Called by every mutation path so the dashboard never shows stale numbers after an action."""
    _cache.invalidate()


def _compute_metrics(db: Session) -> dict:
    # Conditional aggregation collapses what used to be 11 sequential
    # round-trips (one COUNT/SUM per status) into 3 -- one per table --
    # each doing every count/sum for that table in a single pass. This is
    # the hottest read path in the app (every dashboard refresh, on a cache
    # miss every ~3s under load), so the round-trip count matters more here
    # than almost anywhere else in the backend.
    payment_row = db.query(
        func.count(Payment.id),
        func.sum(case((Payment.status == "failed", 1), else_=0)),
        func.sum(case((Payment.status == "success", Payment.amount), else_=0.0)),
    ).one()
    total_transactions, failed_payments, total_revenue = payment_row
    failed_payments = failed_payments or 0
    total_revenue = total_revenue or 0.0

    case_row = db.query(
        func.sum(case((RecoveryCase.recovery_status == "pending", 1), else_=0)),
        func.sum(case((RecoveryCase.recovery_status == "awaiting_payment", 1), else_=0)),
        func.sum(
            case(
                (RecoveryCase.recovery_status == "pending", RecoveryCase.amount_at_risk),
                else_=0.0,
            )
        ),
        func.sum(RecoveryCase.recovered_amount),
        func.sum(case((RecoveryCase.recovery_status == "recovered", 1), else_=0)),
        func.sum(case((RecoveryCase.recovery_status == "failed", 1), else_=0)),
        func.sum(
            case(
                (RecoveryCase.recovery_status.in_(["needs_human_review", "blocked"]), 1),
                else_=0,
            )
        ),
    ).one()
    (
        open_cases,
        awaiting_payment_cases,
        revenue_at_risk,
        recovered_amount,
        successful_recoveries,
        failed_recoveries,
        escalated_cases,
    ) = (value or 0 for value in case_row)

    recovery_attempts = db.query(func.count(Execution.id)).scalar() or 0

    recovery_rate = (
        (
            successful_recoveries
            / (successful_recoveries + failed_recoveries + escalated_cases)
            * 100
        )
        if (successful_recoveries + failed_recoveries + escalated_cases) > 0
        else 0.0
    )

    return {
        "total_revenue": total_revenue,
        "revenue_at_risk": revenue_at_risk,
        "recovered_amount": recovered_amount,
        "recovery_rate": round(recovery_rate, 1),
        "total_transactions": total_transactions,
        "failed_payments": failed_payments,
        "open_cases": open_cases,
        "awaiting_payment_cases": awaiting_payment_cases,
        "recovery_attempts": recovery_attempts,
        "successful_recoveries": successful_recoveries,
        "failed_recoveries": failed_recoveries,
        "escalated_cases": escalated_cases,
        "recovery_cost_per_attempt": settings.RECOVERY_COST_PER_ATTEMPT,
    }
