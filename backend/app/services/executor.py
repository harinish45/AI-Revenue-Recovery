from sqlalchemy.orm import Session
from app.models import RecoveryCase, RecoveryStatus, Payment, AuditLog
from app.services import audit_service

def execute_recovery(db: Session, case_id: int, simulate_success: bool = True):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        return False, "Case not found"
        
    payment = case.payment
    
    if payment.failure_code == "invalid_card":
        case.status = RecoveryStatus.HALTED
        case.retry_count += 1
        audit_service.log_action(db, case_id, "EXECUTION_FAILED", {"reason": "Invalid card, halting retries"})
        db.commit()
        return False, "Halted due to invalid card"
    
    audit_service.log_action(db, case_id, "EXECUTE_INTERVENTION", {
        "strategy": case.intervention_strategy,
        "message_sent": f"Mock message sent to {payment.customer_phone} for {payment.amount}"
    })
    
    case.retry_count += 1
    
    if simulate_success and payment.amount < 10000:
        case.status = RecoveryStatus.RECOVERED
        payment.status = "success"
        audit_service.log_action(db, case_id, "RECOVERY_SUCCESS", {"amount_recovered": payment.amount})
        db.commit()
        return True, "Recovered"
    else:
        case.status = RecoveryStatus.NUDGED
        audit_service.log_action(db, case_id, "NUDGE_SENT", {"retry_count": case.retry_count})
        db.commit()
        return False, "Nudged, awaiting response"
