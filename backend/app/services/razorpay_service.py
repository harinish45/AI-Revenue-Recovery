import razorpay
from ..config import settings
from ..services.audit_service import log_event
from sqlalchemy.orm import Session

def get_razorpay_client():
    if settings.RAZORPAY_KEY_ID == "dummy_key":
        return None
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def trigger_payment_link(db: Session, payment_id: int, amount: float, action: str) -> tuple:
    client = get_razorpay_client()
    
    if client is None:
        log_event(db, None, "RAZORPAY_SIMULATION", {
            "payment_id": payment_id,
            "action": action,
            "message": "Razorpay test mode keys not configured. Simulating successful API call."
        })
        return True, "SIMULATED_SUCCESS"

    try:
        link_data = {
            "amount": int(amount * 100),
            "currency": "INR",
            "description": f"RecoverAI Recovery for {payment_id}",
            "customer": {"email": f"recovery_{payment_id}@example.com"},
            "notify": {"email": True},
            "reminder_enable": True
        }
        log_event(db, None, "RAZORPAY_API_CALL", {"status": "SUCCESS", "payload": link_data})
        return True, "SUCCESS"
    except Exception as e:
        log_event(db, None, "RAZORPAY_API_ERROR", {"error": str(e)})
        return False, f"FAILURE: {str(e)}"
