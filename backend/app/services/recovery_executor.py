import uuid

from sqlalchemy.orm import Session

from ..models import DemoFlag, Execution, IdempotencyKey, Payment, RecoveryCase
from ..services.audit_service import log_event
from ..services.metrics_service import invalidate_metrics_cache
from ..services.policy_engine import evaluate_policy
from ..services.razorpay_service import trigger_payment_link


def execute_recovery(db: Session, case: RecoveryCase, idempotency_key: str = None) -> dict:
    if idempotency_key:
        cached = (
            db.query(IdempotencyKey)
            .filter(IdempotencyKey.key == idempotency_key, IdempotencyKey.endpoint == "execute")
            .first()
        )
        if cached:
            return cached.response

    try:
        result = _run_recovery(db, case)
        if idempotency_key:
            db.add(IdempotencyKey(key=idempotency_key, endpoint="execute", response=result))
        db.commit()
        invalidate_metrics_cache()
        return result
    except Exception:
        db.rollback()
        raise


def _run_recovery(db: Session, case: RecoveryCase) -> dict:
    payment = db.query(Payment).filter(Payment.id == case.payment_id).first()

    flag = db.query(DemoFlag).filter(DemoFlag.id == 1).first()
    if flag and flag.simulate_failure_active:
        flag.simulate_failure_active = False
        case.recovery_status = "needs_human_review"
        case.retry_count += 1
        log_event(
            db,
            case.id,
            "recovery_attempted",
            decision=case.recommended_action,
            action=case.recommended_action,
            result="simulated_failure",
            reason="Demo failure triggered",
        )
        audit = log_event(
            db,
            case.id,
            "escalated_to_human",
            action="human_review",
            reason="Simulated gateway failure handled gracefully",
        )
        return {
            "case_id": case.id,
            "status": "needs_human_review",
            "recovered_amount": 0.0,
            "message": "Simulated gateway failure handled gracefully. Escalated to human review.",
            "audit_event_id": audit.id,
        }

    allowed, checks, reasons = evaluate_policy(db, case, payment)
    case.policy_checks = checks

    if not allowed:
        case.recovery_status = "blocked" if "Max retries" in reasons else "needs_human_review"
        audit = log_event(
            db,
            case.id,
            "policy_check_failed",
            reason="; ".join(reasons),
            action="blocked",
            result="blocked",
        )
        return {
            "case_id": case.id,
            "status": case.recovery_status,
            "recovered_amount": 0.0,
            "message": f"Policy blocked: {'; '.join(reasons)}",
            "audit_event_id": audit.id,
        }

    log_event(
        db,
        case.id,
        "policy_check_passed",
        reason="All checks passed",
        action=case.recommended_action,
    )

    if case.recommended_action in ("retry_payment", "payment_link"):
        is_success, result_msg = trigger_payment_link(
            db, payment.id, payment.amount, case.recommended_action, case.id
        )
    elif case.recommended_action == "customer_reminder":
        is_success, result_msg = True, "SIMULATED_TEST_ACTION: Reminder sent"
    else:
        case.recovery_status = "needs_human_review"
        audit = log_event(
            db,
            case.id,
            "escalated_to_human",
            reason="Requires manual intervention",
            action="human_review",
        )
        return {
            "case_id": case.id,
            "status": "needs_human_review",
            "recovered_amount": 0.0,
            "message": "Escalated to human review.",
            "audit_event_id": audit.id,
        }

    execution = Execution(
        id=f"EXE-{uuid.uuid4().hex[:6].upper()}",
        case_id=case.id,
        action_taken=case.recommended_action,
        result=result_msg,
        amount_recovered=payment.amount if is_success else 0.0,
    )
    db.add(execution)
    case.retry_count += 1

    if is_success:
        case.recovery_status = "recovered"
        case.recovered_amount = payment.amount
        payment.status = "success"
        log_event(
            db,
            case.id,
            "recovery_succeeded",
            action=case.recommended_action,
            result="success",
            reason=result_msg,
        )
        final_status = "recovered"
        msg = (
            "Recovery succeeded in Razorpay Test Mode."
            if "SIMULATED" not in result_msg
            else "Recovery succeeded (Simulated)."
        )
    elif case.retry_count >= case.max_retries:
        case.recovery_status = "needs_human_review"
        log_event(
            db,
            case.id,
            "escalated_to_human",
            action="human_review",
            reason="Max retries reached after failure",
        )
        final_status = "needs_human_review"
        msg = f"Recovery failed after {case.retry_count} attempts: {result_msg}. Escalated."
    else:
        case.recovery_status = "failed"
        log_event(
            db,
            case.id,
            "recovery_failed",
            action=case.recommended_action,
            result="failure",
            reason=result_msg,
        )
        final_status = "failed"
        msg = f"Recovery failed: {result_msg}"

    return {
        "case_id": case.id,
        "status": final_status,
        "recovered_amount": execution.amount_recovered,
        "message": msg,
        "audit_event_id": execution.id,
    }


def run_batch_recovery(db: Session) -> dict:
    pending_cases = (
        db.query(RecoveryCase)
        .filter(RecoveryCase.recovery_status == "pending", RecoveryCase.action_status == "eligible")
        .all()
    )

    total_cases = len(pending_cases)
    amount_at_risk = sum(c.amount_at_risk for c in pending_cases)

    attempted, successful, failed, escalated = 0, 0, 0, 0
    amount_recovered = 0.0

    for case in pending_cases:
        result = execute_recovery(db, case)
        attempted += 1
        if result["status"] == "recovered":
            successful += 1
            amount_recovered += result["recovered_amount"]
        elif result["status"] == "failed":
            failed += 1
        elif result["status"] in ("needs_human_review", "blocked"):
            escalated += 1

    recovery_rate = (amount_recovered / amount_at_risk * 100) if amount_at_risk > 0 else 0.0

    return {
        "total_cases": total_cases,
        "attempted": attempted,
        "successful": successful,
        "failed": failed,
        "escalated": escalated,
        "amount_at_risk": amount_at_risk,
        "amount_recovered": amount_recovered,
        "recovery_rate": round(recovery_rate, 2),
    }
