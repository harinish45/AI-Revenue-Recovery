import random
from datetime import timedelta

from sqlalchemy.orm import Session

from ..models import AuditLog, AuditSeal, Customer, DemoFlag, IdempotencyKey, Payment, RecoveryCase
from .audit_service import log_event
from .decision_engine import diagnose_and_recommend
from .metrics_service import invalidate_metrics_cache
from ..utils.time import utcnow

INDIAN_NAMES = [
    "Arjun Kumar",
    "Priya Sharma",
    "Rahul Verma",
    "Anjali Nair",
    "Vikram Singh",
    "Sneha Patel",
    "Rohan Gupta",
    "Kavya Reddy",
    "Amit Joshi",
    "Deepika Rao",
]
FAILURE_REASONS = [
    ("gateway_timeout", "Gateway timeout", "temporary_gateway_failure"),
    ("insufficient_funds", "Insufficient funds", "customer_liquidity_issue"),
    ("bank_declined", "Bank declined transaction", "bank_rejection"),
    ("invalid_card", "Invalid card details", "invalid_instrument"),
    ("user_abandoned", "User abandoned checkout", "user_abandonment"),
]


def generate_synthetic_data(db: Session):
    db.query(AuditLog).delete()
    db.query(AuditSeal).delete()
    db.query(IdempotencyKey).delete()
    db.query(RecoveryCase).delete()
    db.query(Payment).delete()
    db.query(Customer).delete()
    db.query(DemoFlag).delete()
    flag = DemoFlag(id=1, simulate_failure_active=False)
    db.add(flag)

    customers = []
    for i in range(20):
        c = Customer(
            id=f"cus_{i + 1:03d}",
            name=random.choice(INDIAN_NAMES),
            email=f"customer{i + 1}@recoverai.demo",
            phone=f"+9198{random.randint(10000000, 99999999)}",
        )
        customers.append(c)
    db.add_all(customers)
    db.flush()

    payments = []
    for i in range(70):
        p = Payment(
            id=f"pay_success_{i + 1:03d}",
            customer_id=random.choice(customers).id,
            amount=round(random.uniform(500, 15000), 2),
            status="success",
            timestamp=utcnow() - timedelta(days=random.randint(1, 30)),
        )
        payments.append(p)

    for i in range(20):
        _, reason_text, category = random.choice(FAILURE_REASONS)
        p = Payment(
            id=f"pay_fail_{i + 1:03d}",
            customer_id=random.choice(customers).id,
            amount=round(random.uniform(1000, 25000), 2),
            status="failed",
            failure_reason=reason_text,
            timestamp=utcnow() - timedelta(hours=random.randint(1, 48)),
        )
        payments.append(p)

    for i in range(10):
        p = Payment(
            id=f"pay_other_{i + 1:03d}",
            customer_id=random.choice(customers).id,
            amount=25.0 if i == 0 else round(random.uniform(500, 5000), 2),
            status="abandoned" if i == 0 else random.choice(["pending", "abandoned"]),
            failure_reason="User abandoned checkout" if random.random() > 0.5 else None,
            timestamp=utcnow() - timedelta(hours=random.randint(1, 24)),
        )
        payments.append(p)

    db.add_all(payments)
    db.flush()

    cases_created = 0
    failed_or_abandoned = (
        db.query(Payment).filter(Payment.status.in_(["failed", "abandoned"])).all()
    )

    for payment in failed_or_abandoned:
        customer = db.query(Customer).filter(Customer.id == payment.customer_id).first()
        category, action, reason, evidence, risk_level = diagnose_and_recommend(
            db, payment, customer
        )

        case = RecoveryCase(
            id=f"RC-{payment.id[-6:].upper()}",
            payment_id=payment.id,
            customer_id=customer.id,
            customer_name=customer.name,
            amount_at_risk=payment.amount,
            risk_level=risk_level,
            failure_category=category,
            recommended_action=action,
            reason=reason,
            evidence=evidence,
            policy_checks={},
            retry_count=0,
            max_retries=2,
            recovery_status="pending",
            recovered_amount=0.0,
            action_status="eligible",
            created_at=payment.timestamp,
        )
        db.add(case)

        log_event(
            db,
            case.id,
            "payment_failure_detected",
            reason="Payment failed or abandoned",
            action="case_created",
        )
        log_event(
            db, case.id, "analysis_completed", decision=action, reason=reason, action="diagnosis"
        )
        cases_created += 1

    db.commit()
    invalidate_metrics_cache()
    return len(payments), cases_created
