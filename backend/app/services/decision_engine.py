from sqlalchemy.orm import Session

from ..models import Customer, Payment
from dataclasses import replace

from ..config import settings
from .diagnosis_service import model_suggest_action
from .recovery_agent import choose_intervention


def diagnose_and_recommend(db: Session, payment: Payment, customer: Customer) -> tuple:
    total_payments = db.query(Payment).filter(Payment.customer_id == customer.id).count()
    successful_payments = (
        db.query(Payment)
        .filter(Payment.customer_id == customer.id, Payment.status == "success")
        .count()
    )
    previous_failures = (
        db.query(Payment)
        .filter(Payment.customer_id == customer.id, Payment.status == "failed")
        .count()
    )

    success_rate = (successful_payments / total_payments * 100) if total_payments > 0 else 0

    reason_code = payment.failure_reason.lower() if payment.failure_reason else ""

    evidence = {
        "total_payments": total_payments,
        "successful_payments": successful_payments,
        "previous_failures": previous_failures,
        "success_rate_percent": round(success_rate, 1),
        "current_retry_count": 0,
    }

    decision = choose_intervention(reason_code, success_rate)
    if settings.AI_DIAGNOSIS_ENABLED:
        suggested_action, model_note = model_suggest_action(reason_code, payment.amount)
        if suggested_action:
            decision = replace(decision, action=suggested_action, rationale=model_note, channel="model_assisted")
        evidence["diagnosis_mode"] = "model_assisted" if suggested_action else model_note
    else:
        evidence["diagnosis_mode"] = "deterministic_fallback"
    evidence = decision.as_evidence(evidence)
    return decision.category, decision.action, decision.rationale, evidence, decision.risk_level
