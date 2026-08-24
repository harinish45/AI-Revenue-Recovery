from sqlalchemy.orm import Session

from ..models import Customer, Payment


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

    if "gateway" in reason_code or "timeout" in reason_code:
        category = "temporary_gateway_failure"
        risk_level = "low"
        action = "retry_payment"
        reason = "Transient gateway issue. Customer has good history. Safe to retry."
    elif "insufficient" in reason_code:
        category = "customer_liquidity_issue"
        risk_level = "medium"
        action = "payment_link"
        reason = "Customer lacks funds currently. Send payment link for deferred payment."
    elif "bank" in reason_code:
        category = "bank_rejection"
        risk_level = "high"
        action = "needs_human_review"
        reason = "Bank declined. Requires manual verification or alternate payment method."
    elif "invalid" in reason_code:
        category = "invalid_instrument"
        risk_level = "high"
        action = "needs_human_review"
        reason = "Invalid card details. Potential fraud or typo. Escalate."
    else:
        category = "user_abandonment"
        risk_level = "low"
        action = "customer_reminder"
        reason = "User abandoned checkout. Gentle reminder might recover."

    return category, action, reason, evidence, risk_level
