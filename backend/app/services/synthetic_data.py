import random
from datetime import datetime, timedelta, timezone
from ..models import Payment
from sqlalchemy.orm import Session

FIRST_NAMES = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan",
               "Ananya", "Diya", "Myra", "Sara", "Aadhya", "Kiara", "Siya", "Ahana", "Navya", "Riya"]
LAST_NAMES = ["Sharma", "Verma", "Singh", "Kumar", "Patel", "Reddy", "Nair", "Iyer", "Gupta", "Mehta"]

def generate_synthetic_payments(db: Session, count: int = 100):
    failure_codes = [
        "insufficient_funds", "gateway_timeout", "bank_maintenance", 
        "invalid_card", "user_cancelled", "expired_card"
    ]
    statuses = ["failed", "abandoned"]
    
    random.seed(42)
    
    for i in range(count):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower()}{i}@example.com"
        
        tx_id = f"pay_demo_{i+1:04d}"
        status = random.choice(statuses)
        
        payment = Payment(
            transaction_id=tx_id,
            customer_email=email,
            customer_name=name,
            amount=round(random.uniform(500.0, 60000.0), 2),
            status=status,
            failure_code=random.choice(failure_codes),
            timestamp=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 48))
        )
        db.add(payment)
    db.commit()
    return count
