import random
from datetime import datetime, timedelta
from ..models import Payment
from sqlalchemy.orm import Session

def generate_synthetic_payments(db: Session, count: int = 100):
    failure_codes = [
        "insufficient_funds", "gateway_timeout", "bank_maintenance", 
        "invalid_card", "user_cancelled", "expired_card"
    ]
    statuses = ["failed", "abandoned"]
    
    for i in range(count):
        tx_id = f"tx_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{i}"
        payment = Payment(
            transaction_id=tx_id,
            customer_email=f"user{i}@example.com",
            amount=round(random.uniform(500.0, 60000.0), 2),
            status=random.choice(statuses),
            failure_code=random.choice(failure_codes),
            timestamp=datetime.utcnow() - timedelta(hours=random.randint(1, 48))
        )
        db.add(payment)
    db.commit()
    return count
