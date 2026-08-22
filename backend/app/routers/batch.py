from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import RecoveryCase
from ..schemas import BatchResponse
from ..services.recovery_executor import execute_recovery

router = APIRouter()

@router.post("/process", response_model=BatchResponse)
def process_batch(db: Session = Depends(get_db)):
    pending_cases = db.query(RecoveryCase).filter(RecoveryCase.recovery_status == "pending", RecoveryCase.action_status == "eligible").all()
    
    total_cases = len(pending_cases)
    amount_at_risk = sum(c.amount_at_risk for c in pending_cases)
    
    attempted = 0
    successful = 0
    failed = 0
    escalated = 0
    amount_recovered = 0.0
    
    for case in pending_cases:
        result = execute_recovery(db, case)
        attempted += 1
        if result["status"] == "recovered":
            successful += 1
            amount_recovered += result["recovered_amount"]
        elif result["status"] == "failed":
            failed += 1
        elif result["status"] in ["needs_human_review", "blocked"]:
            escalated += 1
            
    recovery_rate = (amount_recovered / amount_at_risk * 100) if amount_at_risk > 0 else 0.0
    
    return BatchResponse(
        total_cases=total_cases,
        attempted=attempted,
        successful=successful,
        failed=failed,
        escalated=escalated,
        amount_at_risk=amount_at_risk,
        amount_recovered=amount_recovered,
        recovery_rate=round(recovery_rate, 2)
    )
