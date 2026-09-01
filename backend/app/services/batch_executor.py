"""Batch recovery orchestration.

Split out of ``recovery_executor.py``: this drives ``execute_recovery`` over
every eligible pending/failed case and aggregates the results into one
economic summary. It has no execution logic of its own -- a poisoned case
must never abort the whole batch, so each case is isolated in its own
try/except.
"""

import uuid

from sqlalchemy.orm import Session

from ..config import settings
from ..models import RecoveryCase
from ..services.recovery_executor import execute_recovery


def run_batch_recovery(db: Session) -> dict:
    pending_cases = (
        db.query(RecoveryCase)
        .filter(RecoveryCase.recovery_status.in_(["pending", "failed"]))
        .filter(RecoveryCase.action_status == "eligible")
        .all()
    )

    batch_id = f"BATCH-{uuid.uuid4().hex[:8].upper()}"
    total_cases = len(pending_cases)
    amount_at_risk = sum(c.amount_at_risk for c in pending_cases)

    attempted, successful, failed, escalated, skipped, awaiting, errored = 0, 0, 0, 0, 0, 0, 0
    amount_recovered = 0.0

    for case in pending_cases:
        try:
            result = execute_recovery(db, case)
        except Exception:
            # One poisoned case must never abort the whole batch. This is
            # deliberately counted apart from `escalated`: an escalation
            # means the policy engine made a decision and the case record
            # reflects it (needs_human_review/blocked); an unexpected
            # exception here means execute_recovery never got to update the
            # case at all -- db.rollback() undoes any partial write, so the
            # case is left exactly as it was (still pending/eligible), not
            # actually escalated. Folding the two together would make the
            # batch summary claim a case was routed to human review when
            # the case list itself still shows it untouched.
            db.rollback()
            errored += 1
            continue
        attempted += 1
        if result["status"] == "recovered":
            successful += 1
            amount_recovered += result["recovered_amount"]
        elif result["status"] == "awaiting_payment":
            awaiting += 1
        elif result["status"] == "failed":
            failed += 1
        elif result["status"] in ("needs_human_review", "blocked"):
            escalated += 1
        elif result["status"] == "skipped":
            skipped += 1

    recovery_rate = (amount_recovered / amount_at_risk * 100) if amount_at_risk > 0 else 0.0

    return {
        "batch_id": batch_id,
        "total_cases": total_cases,
        "attempted": attempted,
        "successful": successful,
        "awaiting": awaiting,
        "failed": failed,
        "escalated": escalated,
        "amount_at_risk": amount_at_risk,
        "amount_recovered": amount_recovered,
        "recovery_rate": round(recovery_rate, 2),
        "skipped": skipped,
        "errored": errored,
        "estimated_cost": round(attempted * settings.RECOVERY_COST_PER_ATTEMPT, 2),
        "net_recovered": round(
            max(0.0, amount_recovered - attempted * settings.RECOVERY_COST_PER_ATTEMPT), 2
        ),
    }
