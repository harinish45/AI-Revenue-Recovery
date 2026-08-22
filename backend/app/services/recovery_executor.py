from ..models import RecoveryCase, Payment, Execution, DemoFlag
from ..services.policy_engine import evaluate_policy
from ..services.razorpay_service import trigger_payment_link
from ..services.audit_service import log_event
from sqlalchemy.orm import Session
import uuid

def execute_recovery(db: Session, case: RecoveryCase):
    payment = db.query(Payment).filter(Payment.id == case.payment_id).first()
    
    flag = db.query(DemoFlag).filter(DemoFlag.id == 1).first()
    if flag and flag.simulate_failure_active:
        flag.simulate_failure_active = False
        db.commit()
        
        case.recovery_status = "needs_human_review"
        case.retry_count += 1
        db.commit()
        
        log_event(db, case.id, "recovery_attempted", decision=case.recommended_action, action=case.recommended_action, result="simulated_failure", reason="Demo failure triggered")
        log_event(db, case.id, "escalated_to_human", action="human_review", reason="Simulated gateway failure handled gracefully")
        
        return {
            "case_id": case.id,
            "status": "needs_human_review",
            "recovered_amount": 0.0,
            "message": "Simulated gateway failure handled gracefully. Escalated to human review.",
            "audit_event_id": f"AUD-{uuid.uuid4().hex[:6].upper()}"
        }

    allowed, checks, reasons = evaluate_policy(db, case, payment)
    case.policy_checks = checks
    db.commit()

    if not allowed:
        case.recovery_status = "blocked" if "Max retries" in reasons else "needs_human_review"
        db.commit()
        log_event(db, case.id, "policy_check_failed", reason="; ".join(reasons), action="blocked", result="blocked")
        return {
            "case_id": case.id,
            "status": case.recovery_status,
            "recovered_amount": 0.0,
            "message": f"Policy blocked: {'; '.join(reasons)}",
            "audit_event_id": f"AUD-{uuid.uuid4().hex[:6].upper()}"
        }

    log_event(db, case.id, "policy_check_passed", reason="All checks passed", action=case.recommended_action)

    if case.recommended_action == "retry_payment":
        is_success, result_msg = trigger_payment_link(db, payment.id, payment.amount, case.recommended_action, case.id)
    elif case.recommended_action == "payment_link":
        is_success, result_msg = trigger_payment_link(db, payment.id, payment.amount, case.recommended_action, case.id)
    elif case.recommended_action == "customer_reminder":
        is_success, result_msg = True, "SIMULATED_TEST_ACTION: Reminder sent"
    else:
        case.recovery_status = "needs_human_review"
        db.commit()
        log_event(db, case.id, "escalated_to_human", reason="Requires manual intervention", action="human_review")
        return {
            "case_id": case.id,
            "status": "needs_human_review",
            "recovered_amount": 0.0,
            "message": "Escalated to human review.",
            "audit_event_id": f"AUD-{uuid.uuid4().hex[:6].upper()}"
        }

    execution = Execution(
        id=f"EXE-{uuid.uuid4().hex[:6].upper()}",
        case_id=case.id,
        action_taken=case.recommended_action,
        result=result_msg,
        amount_recovered=payment.amount if is_success else 0.0
    )
    db.add(execution)
    
    case.retry_count += 1
    
    if is_success:
        case.recovery_status = "recovered"
        case.recovered_amount = payment.amount
        payment.status = "success"
        log_event(db, case.id, "recovery_succeeded", action=case.recommended_action, result="success", reason=result_msg)
        final_status = "recovered"
        msg = "Recovery succeeded in Razorpay Test Mode." if "SIMULATED" not in result_msg else "Recovery succeeded (Simulated)."
    else:
        if case.retry_count >= case.max_retries:
            case.recovery_status = "needs_human_review"
            log_event(db, case.id, "escalated_to_human", action="human_review", reason="Max retries reached after failure")
        else:
            case.recovery_status = "failed"
            log_event(db, case.id, "recovery_failed", action=case.recommended_action, result="failure", reason=result_msg)
        final_status = "failed"
        msg = f"Recovery failed: {result_msg}"
        
    db.commit()
    
    return {
        "case_id": case.id,
        "status": final_status,
        "recovered_amount": execution.amount_recovered,
        "message": msg,
        "audit_event_id": execution.id
    }
