from ..models import RecoveryCase, Payment
from sqlalchemy.orm import Session

MAX_RETRIES = 2
MAX_AMOUNT = 50000.0

def evaluate_policy(db: Session, case: RecoveryCase, payment: Payment) -> tuple:
    checks = {
        "max_retries_check": True,
        "terminal_state_check": True,
        "amount_limit_check": True,
        "status_check": True
    }
    
    reasons = []

    if case.recovery_status in ["recovered", "blocked", "needs_human_review"]:
        checks["terminal_state_check"] = False
        reasons.append(f"Case is in terminal state: {case.recovery_status}")

    if case.retry_count >= MAX_RETRIES:
        checks["max_retries_check"] = False
        reasons.append("Max retries exceeded")

    if payment.amount > MAX_AMOUNT:
        checks["amount_limit_check"] = False
        reasons.append("Amount exceeds safe automated threshold")

    if payment.status not in ["failed", "abandoned"]:
        checks["status_check"] = False
        reasons.append(f"Payment status {payment.status} is not eligible")

    allowed = all(checks.values())
    
    return allowed, checks, reasons
