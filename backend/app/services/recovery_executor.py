"""Recovery execution service.

Execution order is a hard safety contract:

1. Load the case and its payment record.
2. Escalate safely if the payment record is missing (never a 500).
3. Apply the economic smart-skip rule.
4. Evaluate the deterministic policy engine.
5. Only after policy approval, inject a simulated provider failure (demo).
6. Call the provider, then record the honest lifecycle state:
   ``payment_link`` / ``customer_reminder`` => ``awaiting_payment`` (no money
   is claimed until the provider confirms), ``retry_payment`` => provider
   confirms the direct charge in test mode => ``recovered``.
"""

import uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..models import DemoFlag, Execution, IdempotencyKey, Payment, RecoveryCase
from ..services.audit_service import log_event
from ..services.metrics_service import invalidate_metrics_cache
from ..services.policy_engine import TERMINAL_STATES, evaluate_policy
from ..services.razorpay_service import trigger_payment_link

# Interventions that only *request* money — the provider must confirm before
# any revenue is counted. A direct retry is confirmed synchronously by the
# gateway in test mode.
AWAITING_PROVIDER_ACTIONS = {"payment_link", "customer_reminder"}


def execute_recovery(db: Session, case: RecoveryCase, idempotency_key: str = None) -> dict:
    if idempotency_key:
        cached = (
            db.query(IdempotencyKey)
            .filter(IdempotencyKey.key == idempotency_key, IdempotencyKey.endpoint == "execute")
            .first()
        )
        if cached:
            if cached.response and cached.response.get("case_id") != case.id:
                raise HTTPException(status_code=409, detail="Idempotency-Key is already used for another case")
            return cached.response

    try:
        result = _run_recovery(db, case)
        if idempotency_key:
            db.add(IdempotencyKey(key=idempotency_key, endpoint="execute", response=result))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            cached = db.query(IdempotencyKey).filter(IdempotencyKey.key == idempotency_key, IdempotencyKey.endpoint == "execute").first()
            if cached and cached.response and cached.response.get("case_id") == case.id:
                return cached.response
            raise
        invalidate_metrics_cache()
        return result
    except Exception:
        db.rollback()
        raise


def _escalate(db: Session, case: RecoveryCase, reason: str, decision: str = None) -> dict:
    """Send the case to human review with a sealed audit event."""
    case.recovery_status = "needs_human_review"
    audit = log_event(
        db,
        case.id,
        "escalated_to_human",
        decision=decision,
        action="human_review",
        reason=reason,
    )
    return {
        "case_id": case.id,
        "status": "needs_human_review",
        "recovered_amount": 0.0,
        "message": reason,
        "audit_event_id": audit.id,
    }


def _run_recovery(db: Session, case: RecoveryCase) -> dict:
    payment = db.query(Payment).filter(Payment.id == case.payment_id).first()

    # Safety check 1: a case without its source payment can never be executed.
    if payment is None:
        return _escalate(
            db,
            case,
            "Payment record is missing for this case; automatic recovery is unsafe. Escalated to human review.",
            decision="missing_payment_record",
        )

    # Safety check 2: economic smart-skip (expected value below intervention cost).
    if payment.amount < settings.SMART_SKIP_MIN_AMOUNT:
        case.recovery_status = "skipped"
        case.action_status = "skipped"
        audit = log_event(
            db, case.id, "recovery_skipped", action="smart_skip", result="skipped",
            reason=f"Expected recovery value {payment.amount:.2f} is below the "
                   f"configured intervention floor {settings.SMART_SKIP_MIN_AMOUNT:.2f}.",
        )
        return {
            "case_id": case.id, "status": "skipped", "recovered_amount": 0.0,
            "message": "Smart skip: intervention cost exceeds recovery value.",
            "audit_event_id": audit.id,
        }

    # Safety check 3: the deterministic policy gate.
    allowed, checks, reasons = evaluate_policy(db, case, payment)
    case.policy_checks = checks

    if not allowed:
        # Never overwrite an existing terminal status (e.g. awaiting_payment):
        # the audit trail must preserve the state the case actually reached.
        if case.recovery_status not in TERMINAL_STATES:
            case.recovery_status = (
                "blocked" if not checks.get("max_retries_check", True) else "needs_human_review"
            )
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
            "message": "Policy blocked this action: " + "; ".join(reasons),
            "audit_event_id": audit.id,
        }

    # Safety check 4 (demo only): simulated provider failure AFTER the policy
    # gate, so an armed failure can never bypass amount limits, terminal-state
    # protection, or the action allowlist.
    flag = db.query(DemoFlag).filter(DemoFlag.id == 1).first()
    if flag and flag.simulate_failure_active:
        flag.simulate_failure_active = False
        case.retry_count += 1
        log_event(
            db,
            case.id,
            "recovery_attempted",
            decision=case.recommended_action,
            action=case.recommended_action,
            result="simulated_failure",
            reason="Simulated gateway failure injected after policy approval",
        )
        return _escalate(
            db,
            case,
            "Simulated gateway failure handled gracefully. Escalated to human review.",
        )

    # Provider call happens only after every safety layer passed.
    ok, result_msg = trigger_payment_link(
        db, payment.id, payment.amount, case.recommended_action, case.id
    )
    case.retry_count += 1

    if not ok:
        execution = Execution(
            id=f"EXE-{uuid.uuid4().hex[:6].upper()}",
            case_id=case.id,
            action_taken=case.recommended_action,
            result=result_msg,
            amount_recovered=0.0,
        )
        db.add(execution)
        if case.retry_count >= min(int(case.max_retries or settings.MAX_RETRIES), settings.MAX_RETRIES):
            log_event(
                db,
                case.id,
                "recovery_failed",
                action=case.recommended_action,
                result="failure",
                reason=result_msg,
            )
            return _escalate(
                db,
                case,
                f"Recovery failed after {case.retry_count} attempts: {result_msg}. Escalated.",
            )
        case.recovery_status = "failed"
        audit = log_event(
            db,
            case.id,
            "recovery_failed",
            action=case.recommended_action,
            result="failure",
            reason=result_msg,
        )
        return {
            "case_id": case.id,
            "status": "failed",
            "recovered_amount": 0.0,
            "message": f"Recovery failed: {result_msg}",
            "audit_event_id": audit.id,
        }

    if case.recommended_action in AWAITING_PROVIDER_ACTIONS:
        # An intervention was sent, NOT money received. Revenue is only counted
        # when the provider confirms the payment (webhook or operator).
        case.recovery_status = "awaiting_payment"
        execution = Execution(
            id=f"EXE-{uuid.uuid4().hex[:6].upper()}",
            case_id=case.id,
            action_taken=case.recommended_action,
            result=result_msg,
            amount_recovered=0.0,
        )
        db.add(execution)
        audit = log_event(
            db,
            case.id,
            "intervention_sent",
            action=case.recommended_action,
            result="awaiting_payment",
            reason=f"{result_msg} — awaiting provider payment confirmation.",
        )
        return {
            "case_id": case.id,
            "status": "awaiting_payment",
            "recovered_amount": 0.0,
            "message": "Intervention sent. Awaiting provider payment confirmation before revenue is counted.",
            "audit_event_id": audit.id,
        }

    # Direct retry_payment: the gateway confirms the charge synchronously in
    # test mode, so this is a provider-confirmed recovery.
    execution = Execution(
        id=f"EXE-{uuid.uuid4().hex[:6].upper()}",
        case_id=case.id,
        action_taken=case.recommended_action,
        result=result_msg,
        amount_recovered=payment.amount,
    )
    db.add(execution)
    case.recovery_status = "recovered"
    case.recovered_amount = payment.amount
    payment.status = "success"
    audit = log_event(
        db,
        case.id,
        "recovery_succeeded",
        action=case.recommended_action,
        result="success",
        reason=f"{result_msg} — provider confirmed payment of {payment.amount:.2f}.",
    )
    final_msg = (
        "Recovery succeeded in Razorpay Test Mode."
        if "SIMULATED" not in result_msg
        else "Recovery succeeded (Simulated)."
    )
    return {
        "case_id": case.id,
        "status": "recovered",
        "recovered_amount": execution.amount_recovered,
        "message": final_msg,
        "audit_event_id": audit.id,
    }


def confirm_provider_payment(db: Session, case: RecoveryCase, actor: str = "razorpay_webhook") -> dict:
    """Transition awaiting_payment -> recovered, driven by a provider event."""
    if case.recovery_status != "awaiting_payment":
        return None
    payment = db.query(Payment).filter(Payment.id == case.payment_id).first()
    if payment is None:
        return None
    case.recovery_status = "recovered"
    case.recovered_amount = payment.amount
    payment.status = "success"
    execution = Execution(
        id=f"EXE-{uuid.uuid4().hex[:6].upper()}",
        case_id=case.id,
        action_taken="provider_confirmation",
        result="payment_confirmed",
        amount_recovered=payment.amount,
    )
    db.add(execution)
    audit = log_event(
        db,
        case.id,
        "payment_confirmed",
        actor=actor,
        action="payment_confirmation",
        result="recovered",
        reason=f"Provider confirmed payment of {payment.amount:.2f}.",
    )
    invalidate_metrics_cache()
    return {
        "case_id": case.id,
        "status": "recovered",
        "recovered_amount": payment.amount,
        "message": "Provider confirmed the payment. Revenue recorded.",
        "audit_event_id": audit.id,
    }


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

    attempted, successful, failed, escalated, skipped, awaiting = 0, 0, 0, 0, 0, 0
    amount_recovered = 0.0

    for case in pending_cases:
        try:
            result = execute_recovery(db, case)
        except Exception:
            # One poisoned case must never abort the whole batch.
            db.rollback()
            escalated += 1
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
        "estimated_cost": round(attempted * settings.RECOVERY_COST_PER_ATTEMPT, 2),
        "net_recovered": round(max(0.0, amount_recovered - attempted * settings.RECOVERY_COST_PER_ATTEMPT), 2),
    }



