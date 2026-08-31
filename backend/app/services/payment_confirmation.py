"""Provider-confirmed payment handling.

Split out of ``recovery_executor.py``: this is the one path -- driven by a
Razorpay webhook or an operator's manual confirmation -- that turns an
``awaiting_payment`` case into counted revenue. It shares no state with
single-case execution or batch orchestration, so it lives on its own.
"""

import uuid

from sqlalchemy.orm import Session

from ..models import Execution, Payment, RecoveryCase
from ..services.audit_service import log_event
from ..services.metrics_service import invalidate_metrics_cache


def confirm_provider_payment(
    db: Session, case: RecoveryCase, actor: str = "razorpay_webhook"
) -> dict:
    """Transition awaiting_payment -> recovered, driven by a provider event."""
    if case.recovery_status != "awaiting_payment":
        return None
    payment = db.query(Payment).filter(Payment.id == case.payment_id).first()
    if payment is None:
        return None
    case.recovery_status = "recovered"
    case.recovered_amount = payment.amount
    payment.status = "success"
    execution = Execution(
        id=f"EXE-{uuid.uuid4().hex[:6].upper()}",
        case_id=case.id,
        action_taken="provider_confirmation",
        result="payment_confirmed",
        amount_recovered=payment.amount,
    )
    db.add(execution)
    audit = log_event(
        db,
        case.id,
        "payment_confirmed",
        actor=actor,
        action="payment_confirmation",
        result="recovered",
        reason=f"Provider confirmed payment of {payment.amount:.2f}.",
    )
    invalidate_metrics_cache()
    return {
        "case_id": case.id,
        "status": "recovered",
        "recovered_amount": payment.amount,
        "message": "Provider confirmed the payment. Revenue recorded.",
        "audit_event_id": audit.id,
    }
