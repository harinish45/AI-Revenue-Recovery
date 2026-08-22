from ..models import RecoveryCase, Payment, Execution
from ..services.policy_engine import evaluate_policy
from ..services.razorpay_service import trigger_payment_link
from ..services.audit_service import log_event
from sqlalchemy.orm import Session

def execute_recovery(db: Session, case: RecoveryCase):
    payment = case.payment
    
    # Intentional Failure Simulation
    if payment.failure_code == "invalid_card":
        case.status = "HALTED"
        db.commit()
        log_event(db, case.id, "EXECUTION_HALTED", {
            "reason": "Invalid card detected. Preventing unsafe retry."
        })
        return {"status": "HALTED", "message": "Action blocked due to invalid card."}

    allowed, reason = evaluate_policy(db, case, payment)
    if not allowed:
        if "escalation" in reason.lower() or "Max retries" in reason:
            case.status = "ESCALATED"
        db.commit()
        log_event(db, case.id, "POLICY_REJECTION", {"reason": reason})
        return {"status": case.status, "message": reason}

    case.status = "IN_PROGRESS"
    db.commit()

    is_success, result_msg = trigger_payment_link(db, payment.id, payment.amount, case.recommended_action)
    
    execution = Execution(
        case_id=case.id,
        action_taken=case.recommended_action,
        result=result_msg,
        amount_recovered=payment.amount if is_success else 0.0
    )
    db.add(execution)
    
    if is_success:
        case.status = "RECOVERED"
        case.retry_count += 1
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
