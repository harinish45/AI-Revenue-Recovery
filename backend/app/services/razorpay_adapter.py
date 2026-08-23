"""
razorpay_adapter.py
-------------------
Razorpay Test Mode adapter.

This is the ONLY layer that knows Razorpay SDK details.
All other code calls this adapter — never the SDK directly.

Modes:
  1. REAL TEST MODE — credentials provided (rzp_test_*)
     → Creates actual payment links in Razorpay Test Mode
     → No real money moved (test mode only)

  2. SIMULATION MODE — no credentials provided
     → Logs SIMULATED_TEST_ACTION honestly
     → Returns realistic simulated response
     → Never claims simulation is a real API call
"""
import razorpay
from ..config import settings
from ..services.audit_service import log_event
from sqlalchemy.orm import Session
from typing import Tuple, Optional

# Razorpay sandbox amounts are in paise (1 INR = 100 paise)
PAISE_MULTIPLIER = 100


def _get_razorpay_client() -> Optional[razorpay.Client]:
    """
    Return a Razorpay client if real test-mode credentials are configured.
    Returns None if only dummy/missing credentials.
    """
    key_id = settings.RAZORPAY_KEY_ID
    if not key_id or key_id == "dummy_key" or not key_id.startswith("rzp_test_"):
        return None
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def trigger_payment_recovery(
    db: Session,
    case_id: int,
    payment_id: int,
    customer_email: str,
    customer_name: str,
    amount: float,
    action: str,
) -> Tuple[bool, str, str]:
    """
    Execute a recovery action via Razorpay Test Mode or simulation.

    Args:
        db:             Database session (for audit logging)
        case_id:        Recovery case ID (for audit linkage)
        payment_id:     Payment ID
        customer_email: Customer email for notification
        customer_name:  Customer display name
        amount:         Amount in INR
        action:         Recommended recovery action

    Returns:
        (success: bool, result_code: str, detail: str)
        result_code: SUCCESS | SIMULATED_SUCCESS | GATEWAY_FAILURE | SIMULATED_FAILURE
    """
    client = _get_razorpay_client()

    if client is None:
        return _simulate_action(db, case_id, payment_id, amount, action)

    return _real_razorpay_action(
        db, client, case_id, payment_id, customer_email, customer_name, amount, action
    )


def _simulate_action(
    db: Session,
    case_id: int,
    payment_id: int,
    amount: float,
    action: str,
) -> Tuple[bool, str, str]:
    """
    Simulate a Razorpay action when no real credentials are configured.
    Logs the simulation honestly — never claims to be a real API call.
    """
    log_event(
        db,
        case_id=case_id,
        event_type="RAZORPAY_API_CALL",
        details={
            "mode": "SIMULATION",
            "payment_id": payment_id,
            "action": action,
            "amount_inr": amount,
            "note": "Razorpay Test Mode credentials not configured. SIMULATED_TEST_ACTION.",
        },
        actor="RAZORPAY_ADAPTER",
        decision="SIMULATED",
        action=action,
        result_summary="SIMULATED_TEST_ACTION — no real API call made",
    )
    return True, "SIMULATED_SUCCESS", "Razorpay Test Mode simulated action."


def _real_razorpay_action(
    db: Session,
    client: razorpay.Client,
    case_id: int,
    payment_id: int,
    customer_email: str,
    customer_name: str,
    amount: float,
    action: str,
) -> Tuple[bool, str, str]:
    """
    Invoke Razorpay Test Mode API to create a recovery payment link.
    """
    amount_paise = int(amount * PAISE_MULTIPLIER)
    link_data = {
        "amount": amount_paise,
        "currency": "INR",
        "description": f"RecoverAI Recovery — Case #{case_id}",
        "customer": {
            "name": customer_name,
            "email": customer_email,
        },
        "notify": {"email": True},
        "reminder_enable": True,
        "expire_by": None,  # No expiry for test mode
    }

    try:
        response = client.payment_link.create(link_data)
        short_url = response.get("short_url", "N/A")
        link_id = response.get("id", "N/A")

        log_event(
            db,
            case_id=case_id,
            event_type="RAZORPAY_API_CALL",
            details={
                "mode": "REAL_TEST_MODE",
                "payment_id": payment_id,
                "action": action,
                "amount_paise": amount_paise,
                "link_id": link_id,
                "short_url": short_url,
            },
            actor="RAZORPAY_ADAPTER",
            decision="APPROVED",
            action="CREATE_PAYMENT_LINK",
            result_summary=f"Razorpay Test Mode payment link created: {link_id}",
        )
        return True, "SUCCESS", f"Payment link created: {short_url}"

    except Exception as exc:
        log_event(
            db,
            case_id=case_id,
            event_type="RAZORPAY_API_CALL",
            details={
                "mode": "REAL_TEST_MODE",
                "payment_id": payment_id,
                "action": action,
                "error": str(exc),
            },
            actor="RAZORPAY_ADAPTER",
            decision="FAILED",
            action="CREATE_PAYMENT_LINK",
            result_summary=f"Razorpay API error: {str(exc)}",
        )
        return False, "GATEWAY_FAILURE", f"Razorpay API error: {str(exc)}"
