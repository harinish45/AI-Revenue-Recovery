from sqlalchemy.orm import Session

from ..config import settings
from ..models import Payment, RecoveryCase

TERMINAL_STATES = ("recovered", "blocked", "needs_human_review")


def evaluate_policy(db: Session, case: RecoveryCase, payment: Payment) -> tuple:
    checks = {
        "max_retries_check": True,
        "terminal_state_check": True,
        "amount_limit_check": True,
        "status_check": True,
        "action_allowlist_check": case.recommended_action in {"retry_payment", "payment_link", "customer_reminder", "needs_human_review"},
        "agent_confidence_check": float((case.evidence or {}).get("confidence", 1.0)) >= 0.70,
        "stopping_rules_check": (
            not (case.evidence or {}).get("agent")
            or bool((case.evidence or {}).get("stopping_rules"))
        ),
    }

    reasons = []

    if case.recovery_status in TERMINAL_STATES:
        checks["terminal_state_check"] = False
        reasons.append(f"Case is in terminal state: {case.recovery_status}")

    if case.retry_count >= settings.MAX_RETRIES:
        checks["max_retries_check"] = False
        reasons.append("Max retries exceeded")

    if payment.amount > settings.MAX_AMOUNT:
        checks["amount_limit_check"] = False
        reasons.append("Amount exceeds safe automated threshold")

    if payment.status not in ["failed", "abandoned"]:
        checks["status_check"] = False
        reasons.append(f"Payment status {payment.status} is not eligible")

    if not checks["action_allowlist_check"]:
        reasons.append("Intervention is not on the approved action allowlist")
    if not checks["agent_confidence_check"]:
        reasons.append("Agent confidence is below the safe automation threshold")
    if not checks["stopping_rules_check"]:
        reasons.append("No stopping rules were recorded")

    allowed = all(checks.values())

    return allowed, checks, reasons
