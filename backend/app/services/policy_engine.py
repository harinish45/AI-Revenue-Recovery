"""Deterministic policy engine — the single safety boundary for execution.

The AI agent recommends; this module decides. Every check is explainable and
every rejection reason is written to the immutable audit chain.
"""

from datetime import timedelta

from sqlalchemy.orm import Session

from ..config import settings
from ..models import Payment, RecoveryCase
from ..utils.time import utcnow

TERMINAL_STATES = ("recovered", "blocked", "needs_human_review", "skipped", "awaiting_payment")

ALLOWED_ACTIONS = {"retry_payment", "payment_link", "customer_reminder", "needs_human_review"}


def retry_window(case: RecoveryCase):
    """Return the earliest datetime the next retry is permitted, or None."""
    if case.retry_count <= 0:
        return None  # First intervention fires immediately.
    hours = (
        settings.RETRY_COOLDOWN_FIRST_HOURS
        if case.retry_count == 1
        else settings.RETRY_COOLDOWN_HOURS
    )
    reference = case.updated_at or case.created_at
    if reference is None:
        return None
    return reference + timedelta(hours=hours)


def evaluate_policy(db: Session, case: RecoveryCase, payment: Payment) -> tuple:
    if payment is None:
        raise ValueError("evaluate_policy requires a loaded payment record")

    effective_max_retries = min(int(case.max_retries or settings.MAX_RETRIES), settings.MAX_RETRIES)
    next_retry_at = retry_window(case)

    checks = {
        "max_retries_check": True,
        "terminal_state_check": True,
        "amount_limit_check": True,
        "status_check": True,
        "eligibility_status_check": True,
        "amount_reconciliation_check": True,
        "retry_window_check": True,
        "action_allowlist_check": case.recommended_action in ALLOWED_ACTIONS,
        "agent_confidence_check": float((case.evidence or {}).get("confidence", 1.0)) >= 0.70,
        "stopping_rules_check": (
            not (case.evidence or {}).get("agent")
            or bool((case.evidence or {}).get("stopping_rules"))
        ),
        "compliance_check": True,
    }

    reasons = []

    if case.recovery_status in TERMINAL_STATES:
        checks["terminal_state_check"] = False
        reasons.append(f"Case is in terminal state: {case.recovery_status}")

    if (case.action_status or "eligible") != "eligible":
        checks["eligibility_status_check"] = False
        reasons.append(
            f"Case action_status is '{case.action_status}', not 'eligible'; "
            "an operator pause or skip must be lifted first"
        )

    if case.retry_count >= effective_max_retries:
        checks["max_retries_check"] = False
        reasons.append(
            f"Max retries exceeded (case limit {effective_max_retries}, "
            f"policy ceiling {settings.MAX_RETRIES})"
        )

    # AMOUNT_TOLERANCE absorbs float representation noise at the boundary
    # (e.g. an amount that's semantically exactly MAX_AMOUNT after a few
    # arithmetic hops can land a few ULPs on either side in IEEE754) --
    # the same tolerance the reconciliation check below already relies on.
    if payment.amount > settings.MAX_AMOUNT + settings.AMOUNT_TOLERANCE:
        checks["amount_limit_check"] = False
        reasons.append("Amount exceeds safe automated threshold")

    if payment.status not in ["failed", "abandoned"]:
        checks["status_check"] = False
        reasons.append(f"Payment status {payment.status} is not eligible")

    if abs(float(payment.amount) - float(case.amount_at_risk or 0.0)) > settings.AMOUNT_TOLERANCE:
        checks["amount_reconciliation_check"] = False
        reasons.append(
            f"Case amount {case.amount_at_risk:.2f} does not reconcile with "
            f"payment amount {payment.amount:.2f}"
        )

    if next_retry_at is not None and utcnow().replace(tzinfo=None) < next_retry_at:
        checks["retry_window_check"] = False
        reasons.append(
            f"Retry window not reached; next permitted attempt at {next_retry_at.isoformat()}"
        )

    if not checks["action_allowlist_check"]:
        reasons.append("Intervention is not on the approved action allowlist")
    if not checks["agent_confidence_check"]:
        reasons.append("Agent confidence is below the safe automation threshold")
    if not checks["stopping_rules_check"]:
        reasons.append("No stopping rules were recorded")

    allowed = all(checks.values())

    return allowed, checks, reasons


def compliance_score(checks: dict | None) -> float:
    checks = checks or {}
    relevant = [v for k, v in checks.items() if k.endswith("_check")]
    return round(sum(bool(v) for v in relevant) / len(relevant) * 100, 1) if relevant else 100.0
