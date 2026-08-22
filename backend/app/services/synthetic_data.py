import random
import string
from sqlalchemy.orm import Session
from app.models import Payment, PaymentStatus

FAILURE_CODES = [
    ("gateway_timeout", "Payment gateway timed out"),
    ("insufficient_funds", "Customer has insufficient funds"),
    ("bank_maintenance", "Bank under maintenance"),
    ("network_error", "Network error during transaction"),
    ("user_cancelled", "User cancelled the transaction"),
    ("invalid_card", "Invalid card details"),
]

def generate_synthetic_data(db: Session, count: int = 100):
    payments = []
    for i in range(count):
        code, reason = random.choice(FAILURE_CODES)
        amount = round(random.uniform(100.0, 75000.0), 2)
        payment = Payment(
            razorpay_payment_id=f"pay_{''.join(random.choices(string.ascii_lowercase + string.digits, k=14))}",
            customer_id=f"cust_{''.join(random.choices(string.ascii_lowercase + string.digits, k=14))}",
            customer_email=f"customer{i}@example.com",
            customer_phone=f"+9198765{random.randint(10000, 99999)}",
            amount=amount,
            status=PaymentStatus.FAILED,
            failure_code=code,
            failure_reason=reason,
        )
        payments.append(payment)
    
    db.add_all(payments)
    db.commit()
    return len(payments)
