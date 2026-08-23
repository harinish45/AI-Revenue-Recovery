"""
synthetic_data.py
-----------------
Deterministic demo data generator.

Uses random.seed(42) to guarantee identical data on every seed call.
Produces realistic Indian customer names and INR amounts.
Transaction IDs follow: pay_demo_001 ... pay_demo_100
"""
import random
from datetime import datetime, timedelta
from ..models import Payment
from sqlalchemy.orm import Session

# Fixed seed — same data every run
DEMO_SEED = 42

# Realistic Indian customer dataset
INDIAN_NAMES = [
    "Aarav Sharma", "Vivaan Patel", "Aditya Kumar", "Vihaan Gupta",
    "Arjun Reddy", "Sai Krishnan", "Reyansh Mehta", "Ayaan Khan",
    "Atharv Joshi", "Dhruv Nair", "Ananya Singh", "Diya Iyer",
    "Kavya Pillai", "Anika Bose", "Aadhya Chatterjee", "Myra Verma",
    "Priya Agarwal", "Nisha Pandey", "Pooja Rao", "Sunita Mishra",
    "Rahul Malhotra", "Vikram Saxena", "Rohit Tiwari", "Suresh Yadav",
    "Mohan Das", "Rajesh Sinha", "Amit Bajaj", "Kiran Kapoor",
    "Deepa Kulkarni", "Meera Desai", "Shreya Chauhan", "Neha Ghosh",
    "Tanvi Tripathi", "Riya Banerjee", "Ishaan Srivastava", "Kabir Garg",
    "Pranav Oberoi", "Kartik Ahuja", "Varun Sethi", "Nikhil Choudhury",
    "Lakshmi Venkat", "Suja Nambiar", "Geetha Nair", "Revathi Pillai",
    "Divya Menon", "Anjali Krishnan", "Smita Joshi", "Rekha Bhat",
    "Sudha Rao", "Uma Devi",
]

PHONE_PREFIXES = ["98", "87", "99", "76", "85", "70", "96", "91"]

FAILURE_CODES = [
    "insufficient_funds",   # 30% — most recoverable
    "gateway_timeout",      # 20% — retry candidates
    "bank_maintenance",     # 15% — retry candidates
    "invalid_card",         # 10% — halt
    "user_cancelled",       # 15% — nudge
    "expired_card",         # 10% — card update
]

FAILURE_WEIGHTS = [30, 20, 15, 10, 15, 10]

STATUSES = ["failed", "abandoned"]
STATUS_WEIGHTS = [70, 30]

# Amount bands (paisa ranges in INR)
AMOUNT_BANDS = [
    (500.0, 5000.0),     # Low value
    (5001.0, 20000.0),   # Mid value
    (20001.0, 49999.0),  # High value (just under MAX_AMOUNT threshold)
]

BAND_WEIGHTS = [50, 35, 15]


def _random_phone(rng: random.Random) -> str:
    prefix = rng.choice(PHONE_PREFIXES)
    suffix = "".join([str(rng.randint(0, 9)) for _ in range(8)])
    return f"+91-{prefix}{suffix}"


def generate_synthetic_payments(db: Session, count: int = 100) -> int:
    """
    Generate deterministic synthetic payments.

    Args:
        db:    SQLAlchemy session
        count: Number of payments to create (default 100)

    Returns:
        Number of payments created.
    """
    rng = random.Random(DEMO_SEED)

    for i in range(1, count + 1):
        tx_id = f"pay_demo_{i:03d}"
        name = INDIAN_NAMES[i % len(INDIAN_NAMES)]
        email_local = name.lower().replace(" ", ".") + str(i)
        email = f"{email_local}@example.in"
        phone = _random_phone(rng)

        failure_code = rng.choices(FAILURE_CODES, weights=FAILURE_WEIGHTS, k=1)[0]
        status = rng.choices(STATUSES, weights=STATUS_WEIGHTS, k=1)[0]

        # Pick amount band then pick amount within band
        band = rng.choices(AMOUNT_BANDS, weights=BAND_WEIGHTS, k=1)[0]
        amount = round(rng.uniform(band[0], band[1]), 2)

        # Spread timestamps over last 48 hours
        hours_ago = rng.randint(1, 48)

        payment = Payment(
            transaction_id=tx_id,
            customer_name=name,
            customer_email=email,
            customer_phone=phone,
            amount=amount,
            currency="INR",
            status=status,
            failure_code=failure_code,
            timestamp=datetime.utcnow() - timedelta(hours=hours_ago),
        )
        db.add(payment)

    db.commit()
    return count
