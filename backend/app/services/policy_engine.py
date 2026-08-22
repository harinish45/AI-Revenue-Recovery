from sqlalchemy.orm import Session
from app.models import RecoveryCase, RecoveryStatus, Payment
from app.core.config import settings

def check_policies(db: Session, case_id: int):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        return False, "Case not found"
        
    payment = case.payment
    
    if case.retry_count >= settings.MAX_RETRIES:
        return False, f"Max retries ({settings.MAX_RETRIES}) exceeded"
        
    if payment.amount > settings.MAX_AMOUNT:
        return False, f"Amount {payment.amount} exceeds max allowed {settings.MAX_AMOUNT}"
        
    if case.status not in [RecoveryStatus.OPEN, RecoveryStatus.NUDGED]:
        return False, f"Case status {case.status} is not eligible for execution"
        
    if payment.amount > settings.ESCALATION_THRESHOLD:
        return False, "ESCALATE"
        
    return True, "Approved"
