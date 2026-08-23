"""
policy_engine.py
----------------
Deterministic backend policy layer.

This is the final authority on whether a recovery action is allowed.
The LLM/decision engine recommendation is ONLY a suggestion.
The policy engine must approve every action before execution.

Hard rules:
  1. Terminal state check — no re-execution of RECOVERED/HALTED/ESCALATED cases
  2. Max retries (attempt_count >= MAX_RETRIES) → escalate
  3. High-value transactions (amount > MAX_AMOUNT) → human review
  4. Non-recoverable payment status → block
  5. Low confidence recommendation → human review
  6. Failure simulation armed → controlled failure
"""
from ..models import RecoveryCase, Payment
from ..services.audit_service import log_event
from sqlalchemy.orm import Session
from typing import Tuple

# ---------------------------------------------------------------------------
# Policy constants
# ---------------------------------------------------------------------------
MAX_RETRIES: int = 3          # max attempt_count before escalation
MAX_AMOUNT: float = 50000.0   # INR — above this, always human review
MIN_CONFIDENCE: float = 0.50  # below this, human review
TERMINAL_STATES = {"RECOVERED", "HALTED", "ESCALATED", "NEEDS_HUMAN_REVIEW"}


def evaluate_policy(db: Session, case: RecoveryCase, payment: Payment) -> Tuple[bool, str]:
    """
    Evaluate whether recovery execution is policy-allowed.

    Args:
        db:      Database session
        case:    The RecoveryCase to evaluate
        payment: The associated Payment record

    Returns:
        (allowed: bool, reason: str)
    """
    # Rule 1: Terminal state check
    if case.status in TERMINAL_STATES:
        reason = f"Policy blocked: Case is in terminal state [{case.status}]. No further recovery."
        _log_rejection(db, case, payment, reason)
        return False, reason

    # Rule 2: Max attempts exceeded
    if case.attempt_count >= MAX_RETRIES:
        reason = (
            f"Policy blocked: Max retries exceeded "
            f"(attempts={case.attempt_count}, max={MAX_RETRIES}). "
            f"Escalating to human review."
        )
        _log_rejection(db, case, payment, reason, decision="ESCALATE")
        return False, reason

    # Rule 3: High-value transaction
    if payment.amount > MAX_AMOUNT:
        reason = (
            f"Policy blocked: Transaction amount ₹{payment.amount:,.2f} exceeds "
            f"automated recovery limit of ₹{MAX_AMOUNT:,.0f}. Human review required."
        )
        _log_rejection(db, case, payment, reason, decision="ESCALATE")
        return False, reason

    # Rule 4: Payment status not recoverable
    if payment.status not in {"failed", "abandoned"}:
        reason = (
            f"Policy blocked: Payment status [{payment.status}] is not eligible "
            f"for automated recovery."
        )
        _log_rejection(db, case, payment, reason)
        return False, reason

    # Rule 5: Low-confidence recommendation
    if case.confidence < MIN_CONFIDENCE and case.recommended_action not in {"HALT_AND_ALERT", "ESCALATE_TO_HUMAN"}:
        reason = (
            f"Policy blocked: AI confidence {case.confidence:.0%} is below "
            f"minimum threshold of {MIN_CONFIDENCE:.0%}. Human review required."
        )
        _log_rejection(db, case, payment, reason, decision="HUMAN_REVIEW")
        return False, reason

    # All checks passed
    log_event(
        db,
        case_id=case.id,
        event_type="POLICY_CHECK",
        details={
            "status": "APPROVED",
            "attempt_count": case.attempt_count,
            "amount": payment.amount,
            "confidence": case.confidence,
            "recommended_action": case.recommended_action,
        },
        actor="POLICY_ENGINE",
        decision="APPROVED",
        action=case.recommended_action,
        result_summary="Policy approved — recovery execution authorized",
    )
    return True, "Policy approved"


def _log_rejection(
    db: Session,
    case: RecoveryCase,
    payment: Payment,
    reason: str,
    decision: str = "REJECTED",
) -> None:
    """Log a policy rejection event."""
    log_event(
        db,
        case_id=case.id,
        event_type="POLICY_CHECK",
        details={
            "status": "REJECTED",
            "reason": reason,
            "attempt_count": case.attempt_count,
            "amount": payment.amount,
        },
        actor="POLICY_ENGINE",
        decision=decision,
        action="BLOCKED",
        result_summary=reason,
    )
