from ..models import Payment
from ..services.audit_service import log_event
from sqlalchemy.orm import Session

def diagnose_and_recommend(db: Session, payment: Payment) -> tuple:
    code = payment.failure_code
    diagnosis = ""
    action = ""

    if code == "insufficient_funds":
        diagnosis = "Customer lacks funds. High intent, low liquidity."
        action = "OFFER_SPLIT_PAYMENT"
    elif code in ["gateway_timeout", "bank_maintenance"]:
        diagnosis = "Transient banking/network issue."
        action = "SEND_RETRY_LINK"
    elif code == "invalid_card":
        diagnosis = "Card details incorrect or fraudulent attempt."
        action = "HALT_AND_ALERT"
    elif code == "expired_card":
        diagnosis = "Card on file is expired."
        action = "REQUEST_CARD_UPDATE"
    elif code == "user_cancelled":
        diagnosis = "Customer abandoned checkout intentionally."
        action = "SEND_REMINDER_NUDGE"
    else:
        diagnosis = "Unknown failure."
        action = "ESCALATE_TO_HUMAN"

    log_event(db, None, "LLM_DIAGNOSIS", {
        "payment_id": payment.id,
        "failure_code": code,
        "diagnosis": diagnosis,
        "recommended_action": action
    })
    
    return diagnosis, action
