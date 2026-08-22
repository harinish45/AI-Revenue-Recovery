from sqlalchemy.orm import Session
from app.models import Payment, RecoveryCase, RecoveryStatus, PaymentStatus

def generate_recovery_cases(db: Session):
    existing_case_payment_ids = db.query(RecoveryCase.payment_id).filter(
        RecoveryCase.status.in_([RecoveryStatus.OPEN, RecoveryStatus.NUDGED, RecoveryStatus.RECOVERED, RecoveryStatus.ESCALATED, RecoveryStatus.HALTED])
    ).subquery()

    payments_to_process = db.query(Payment).filter(
        Payment.status == PaymentStatus.FAILED,
        ~Payment.id.in_(existing_case_payment_ids)
    ).all()

    new_cases = []
    for payment in payments_to_process:
        case = RecoveryCase(
            payment_id=payment.id,
            status=RecoveryStatus.OPEN,
            root_cause_diagnosis="Pending Diagnosis",
            intervention_strategy="Pending Strategy"
        )
        new_cases.append(case)
    
    if new_cases:
        db.add_all(new_cases)
        db.commit()
    
    return len(new_cases)
