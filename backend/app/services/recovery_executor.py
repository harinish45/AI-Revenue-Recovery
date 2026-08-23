from ..models import RecoveryCase, Payment, Execution
from ..services.policy_engine import evaluate_policy
from ..services.razorpay_service import trigger_payment_link
from ..services.audit_service import log_event
from sqlalchemy.orm import Session
from datetime import datetime, timezone

SIMULATE_FAILURE_FLAG = False

def arm_failure_simulation():
    global SIMULATE_FAILURE_FLAG
    SIMULATE_FAILURE_FLAG = True

def execute_recovery(db: Session, case: RecoveryCase):
    global SIMULATE_FAILURE_FLAG
    payment = case.payment
    
    if payment.failure_code == "invalid_card":
        case.status = "HALTED"
        db.commit()
        log_event(db, case.id, "EXECUTION_HALTED", {
            "reason": "Invalid card detected. Preventing unsafe retry."
        })
        return {"status": "HALTED", "message": "Action blocked due to invalid card."}

    allowed, reason = evaluate_policy(db, case, payment)
    if not allowed:
        case.status = "ESCALATED"
        db.commit()
        log_event(db, case.id, "POLICY_REJECTION_ESCALATION", {"reason": reason})
        return {"status": "ESCALATED", "message": reason}

    case.status = "IN_PROGRESS"
    db.commit()

    if SIMULATE_FAILURE_FLAG:
        SIMULATE_FAILURE_FLAG = False
        case.status = "needs_human_review"
        case.retry_count += 1
        db.commit()
        log_event(db, case.id, "GATEWAY_FAILURE_SIMULATED", {
            "reason": "Simulated gateway failure handled gracefully. Escalated to human review."
        })
        return {
            "status": "needs_human_review",
            "recovered_amount": 0.0,
            "message": "Simulated gateway failure handled gracefully. Escalated to human review."
        }

    is_success, result_msg = trigger_payment_link(db, payment.id, payment.amount, case.recommended_action)
    
    execution = Execution(
        case_id=case.id,
        action_taken=case.recommended_action,
        result=result_msg,
        amount_recovered=payment.amount if is_success else 0.0,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(execution)
    
    if is_success:
        case.status = "RECOVERED"
    else:
        case.retry_count += 1
        if case.retry_count >= 3:
            case.status = "ESCALATED"
            
    db.commit()
    
    log_event(db, case.id, "EXECUTION_COMPLETE", {
        "success": is_success,
        "result": result_msg,
        "amount_recovered": execution.amount_recovered
    })
    
    return {
        "status": case.status,
        "action": case.recommended_action,
        "result": result_msg,
        "amount_recovered": execution.amount_recovered
    }
