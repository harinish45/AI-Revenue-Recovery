import razorpay
from sqlalchemy.orm import Session

from ..config import settings
from ..services.audit_service import log_event


def get_razorpay_client():
    if (
        settings.RAZORPAY_SIMULATE
        or not settings.RAZORPAY_KEY_ID
        or not settings.RAZORPAY_KEY_SECRET
    ):
        return None
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def trigger_payment_link(
    db: Session, payment_id: str, amount: float, action: str, case_id: str
) -> tuple:
    client = get_razorpay_client()

    if client is None:
        log_event(
            db,
            case_id,
            "razorpay_simulation",
            actor="razorpay_service",
            action=action,
            result="simulated_success",
            reason="Razorpay test keys not configured. Simulating API call.",
        )
        return True, "SIMULATED_TEST_ACTION: Success"

    link_data = {
        "amount": int(amount * 100),
        "currency": "INR",
        "description": f"RecoverAI Recovery for {payment_id}",
        "customer": {"email": f"recovery_{payment_id}@recoverai.demo"},
        "notify": {"email": True},
        "reminder_enable": False,
    }
    try:
        link = client.payment_link.create(link_data)
        log_event(
            db,
            case_id,
            "razorpay_api_call",
            actor="razorpay_service",
            action=action,
            result="success",
            reason=f"Payment link created: {link.get('short_url', link.get('id'))}",
        )
        return True, "SUCCESS"
    except Exception as e:
        log_event(
            db,
            case_id,
            "razorpay_api_error",
            actor="razorpay_service",
            action=action,
            result="failure",
            reason=str(e),
        )
        return False, f"FAILURE: {str(e)}"
