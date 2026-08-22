from ..models import RecoveryCase, Payment
from ..services.audit_service import log_event
from sqlalchemy.orm import Session

MAX_RETRIES = 3
MAX_AMOUNT = 50000.0

def evaluate_policy(db: Session, case: RecoveryCase, payment: Payment) -> tuple:
    if case.status in ["RECOVERED", "HALTED", "ESCALATED"]:
        return False, f"Policy blocked: Case already in terminal state {case.status}"

    if case.retry_count >= MAX_RETRIES:
        return False, "Policy blocked: Max retries exceeded"

    if payment.amount > MAX_AMOUNT:
        return False, "Policy blocked: High value transaction requires human escalation"

    if payment.status not in ["failed", "abandoned"]:
        return False, f"Policy blocked: Payment status {payment.status} is not eligible"

    log_event(db, case.id, "POLICY_CHECK", {
        "status": "APPROVED",
        "retry_count": case.retry_count,
        "amount": payment.amount
    })
    
    return True, "Policy approved"
