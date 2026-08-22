from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Payment, PaymentStatus, RecoveryCase, RecoveryStatus

def calculate_revenue_at_risk(db: Session):
    recovered_payment_ids = db.query(RecoveryCase.payment_id).filter(
        RecoveryCase.status == RecoveryStatus.RECOVERED
    ).subquery()

    at_risk = db.query(func.sum(Payment.amount)).filter(
        Payment.status == PaymentStatus.FAILED,
        ~Payment.id.in_(recovered_payment_ids)
    ).scalar() or 0.0
    return float(at_risk)

def calculate_recovered_amount(db: Session):
    recovered_payment_ids = db.query(RecoveryCase.payment_id).filter(
        RecoveryCase.status == RecoveryStatus.RECOVERED
    ).subquery()

    recovered = db.query(func.sum(Payment.amount)).filter(
        Payment.id.in_(recovered_payment_ids)
    ).scalar() or 0.0
    return float(recovered)
