"""
recovery_executor.py
--------------------
Recovery execution orchestrator.

Workflow:
  1. Check failure simulation flag (controlled demo failure)
  2. Evaluate policy (deterministic backend rules)
  3. Log EXECUTION_STARTED
  4. Call Razorpay adapter
  5. Record Execution row
  6. Update case status and counters
  7. Log EXECUTION_COMPLETE or ESCALATED_TO_HUMAN
  8. Return structured result

Key design:
  - attempt_count tracks every attempt (including failures)
  - retry_count tracks only successful recovery attempts
  - amount_recovered is cumulative on the case
"""
from ..models import RecoveryCase, Payment, Execution
from ..services.policy_engine import evaluate_policy
from ..services.razorpay_adapter import trigger_payment_recovery
from ..services.audit_service import log_event
from ..services.failure_state import consume_failure
from sqlalchemy.orm import Session
from datetime import datetime


def execute_recovery(db: Session, case: RecoveryCase) -> dict:
    """
    Execute a recovery action for the given case.

    Args:
        db:   Database session
        case: The RecoveryCase to execute

    Returns:
        Structured result dict:
        {
            "status": str,
            "action": str,
            "result": str,
            "amount_recovered": float,
            "message": str
        }
    """
    payment = case.payment

    # -----------------------------------------------------------------------
    # Step 1: Check failure simulation flag
    # If armed, produce a controlled gateway failure for demo purposes.
    # -----------------------------------------------------------------------
    if consume_failure():
        return _handle_gateway_failure(db, case, payment)

    # -----------------------------------------------------------------------
    # Step 2: HALT_AND_ALERT fast-path (no policy evaluation needed)
    # invalid_card cases are halted immediately
    # -----------------------------------------------------------------------
    if case.recommended_action == "HALT_AND_ALERT":
        return _halt_case(db, case, "Invalid card detected. Recovery halted to prevent unsafe retry.")

    # -----------------------------------------------------------------------
    # Step 3: Evaluate backend policy
    # -----------------------------------------------------------------------
    allowed, reason = evaluate_policy(db, case, payment)
    if not allowed:
        if "Max retries" in reason or "escalat" in reason.lower():
            return _escalate_case(db, case, reason)
        elif "Human review" in reason or "human" in reason.lower():
            return _needs_human_review(db, case, reason)
        else:
            case.status = "HALTED"
            db.commit()
            return {
                "status": "HALTED",
                "action": case.recommended_action,
                "result": "POLICY_BLOCKED",
                "amount_recovered": 0.0,
                "message": reason,
            }

    # -----------------------------------------------------------------------
    # Step 4: Increment attempt count and mark IN_PROGRESS
    # -----------------------------------------------------------------------
    case.attempt_count += 1
    case.status = "IN_PROGRESS"
    db.commit()

    log_event(
        db,
        case_id=case.id,
        event_type="EXECUTION_STARTED",
        details={
            "action": case.recommended_action,
            "attempt_count": case.attempt_count,
            "amount": payment.amount,
        },
        actor="RECOVERY_EXECUTOR",
        action=case.recommended_action,
        result_summary=f"Executing {case.recommended_action} for ₹{payment.amount:,.2f}",
    )

    # -----------------------------------------------------------------------
    # Step 5: Call Razorpay adapter
    # -----------------------------------------------------------------------
    success, result_code, detail = trigger_payment_recovery(
        db=db,
        case_id=case.id,
        payment_id=payment.id,
        customer_email=payment.customer_email,
        customer_name=payment.customer_name or "Customer",
        amount=payment.amount,
        action=case.recommended_action,
    )

    # -----------------------------------------------------------------------
    # Step 6: Record Execution row
    # -----------------------------------------------------------------------
    amount_recovered = payment.amount if success else 0.0
    execution = Execution(
        case_id=case.id,
        action_taken=case.recommended_action,
        result=result_code,
        amount_recovered=amount_recovered,
        timestamp=datetime.utcnow(),
    )
    db.add(execution)

    # -----------------------------------------------------------------------
    # Step 7: Update case status and counters
    # -----------------------------------------------------------------------
    if success:
        case.status = "RECOVERED"
        case.retry_count += 1
        case.amount_recovered = (case.amount_recovered or 0.0) + amount_recovered
    else:
        if case.attempt_count >= 3:
            case.status = "ESCALATED"
        else:
            case.status = "OPEN"

    db.commit()

    # -----------------------------------------------------------------------
    # Step 8: Log completion
    # -----------------------------------------------------------------------
    log_event(
        db,
        case_id=case.id,
        event_type="EXECUTION_COMPLETE" if success else "RECOVERY_FAILED",
        details={
            "success": success,
            "result_code": result_code,
            "detail": detail,
            "amount_recovered": amount_recovered,
            "attempt_count": case.attempt_count,
        },
        actor="RECOVERY_EXECUTOR",
        decision="SUCCESS" if success else "FAILED",
        action=case.recommended_action,
        result_summary=f"{'Recovered' if success else 'Failed'} ₹{amount_recovered:,.2f}",
    )

    return {
        "status": case.status,
        "action": case.recommended_action,
        "result": result_code,
        "amount_recovered": amount_recovered,
        "message": detail,
    }


def _halt_case(db: Session, case: RecoveryCase, reason: str) -> dict:
    """Halt recovery permanently (e.g. invalid card)."""
    case.status = "HALTED"
    db.commit()
    log_event(
        db,
        case_id=case.id,
        event_type="EXECUTION_COMPLETE",
        details={"reason": reason},
        actor="RECOVERY_EXECUTOR",
        decision="HALTED",
        action="HALT_AND_ALERT",
        result_summary=reason,
    )
    return {
        "status": "HALTED",
        "action": "HALT_AND_ALERT",
        "result": "HALTED",
        "amount_recovered": 0.0,
        "message": reason,
    }


def _escalate_case(db: Session, case: RecoveryCase, reason: str) -> dict:
    """Escalate case to human review (max retries exceeded)."""
    case.status = "ESCALATED"
    db.commit()
    log_event(
        db,
        case_id=case.id,
        event_type="ESCALATED_TO_HUMAN",
        details={"reason": reason, "attempt_count": case.attempt_count},
        actor="POLICY_ENGINE",
        decision="ESCALATED",
        action="ESCALATE_TO_HUMAN",
        result_summary=f"Escalated to human review: {reason}",
    )
    return {
        "status": "ESCALATED",
        "action": "ESCALATE_TO_HUMAN",
        "result": "ESCALATED",
        "amount_recovered": 0.0,
        "message": reason,
    }


def _needs_human_review(db: Session, case: RecoveryCase, reason: str) -> dict:
    """Mark case as needing human review (policy soft-block)."""
    case.status = "NEEDS_HUMAN_REVIEW"
    db.commit()
    log_event(
        db,
        case_id=case.id,
        event_type="ESCALATED_TO_HUMAN",
        details={"reason": reason},
        actor="POLICY_ENGINE",
        decision="NEEDS_HUMAN_REVIEW",
        action="ESCALATE_TO_HUMAN",
        result_summary=f"Human review required: {reason}",
    )
    return {
        "status": "NEEDS_HUMAN_REVIEW",
        "action": "ESCALATE_TO_HUMAN",
        "result": "NEEDS_HUMAN_REVIEW",
        "amount_recovered": 0.0,
        "message": "Escalated to Human Review. " + reason,
    }


def _handle_gateway_failure(db: Session, case: RecoveryCase, payment: Payment) -> dict:
    """
    Handle a deterministic failure simulation event.
    Used for demo purposes to show the escalation path.
    """
    case.attempt_count += 1
    case.status = "NEEDS_HUMAN_REVIEW"
    db.commit()

    log_event(
        db,
        case_id=case.id,
        event_type="ESCALATED_TO_HUMAN",
        details={
            "reason": "Failure simulation armed — controlled gateway failure triggered",
            "amount": payment.amount,
            "attempt_count": case.attempt_count,
        },
        actor="FAILURE_SIMULATOR",
        decision="ESCALATED",
        action="ESCALATE_TO_HUMAN",
        result_summary="Gateway failure simulation — case escalated to human review",
    )

    return {
        "status": "NEEDS_HUMAN_REVIEW",
        "action": "ESCALATE_TO_HUMAN",
        "result": "GATEWAY_FAILURE",
        "amount_recovered": 0.0,
        "message": "Escalated to Human Review due to gateway failure.",
    }
