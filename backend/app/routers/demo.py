from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import RecoveryCase, DemoFlag
from ..services.synthetic_data import generate_synthetic_data
from ..services.recovery_executor import execute_recovery
from ..schemas import SeedResponse, BatchResponse, SimulateFailureResponse

router = APIRouter()

@router.post("/seed", response_model=SeedResponse)
def seed_database(db: Session = Depends(get_db)):
    records, cases = generate_synthetic_data(db)
    return SeedResponse(created_records=records, message=f"Demo dataset seeded with {records} payments and {cases} recovery cases.")

@router.post("/reset")
def reset_database(db: Session = Depends(get_db)):
    from ..models import AuditLog, Execution, Payment, Customer
    db.query(AuditLog).delete()
    db.query(Execution).delete()
    db.query(RecoveryCase).delete()
    db.query(Payment).delete()
    db.query(Customer).delete()
    db.query(DemoFlag).delete()
    db.commit()
    return {"message": "Database reset complete."}

@router.post("/recovery-batch", response_model=BatchResponse)
def run_batch_recovery(db: Session = Depends(get_db)):
    pending_cases = db.query(RecoveryCase).filter(RecoveryCase.recovery_status == "pending", RecoveryCase.action_status == "eligible").all()
    
    processed = 0
    successful = 0
    failed = 0
    escalated = 0
    total_recovered = 0.0
    
    for case in pending_cases:
        result = execute_recovery(db, case)
        processed += 1
        if result["status"] == "recovered":
            successful += 1
            total_recovered += result["recovered_amount"]
        elif result["status"] == "failed":
            failed += 1
        elif result["status"] in ["needs_human_review", "blocked"]:
            escalated += 1
            
    return BatchResponse(
        processed=processed,
        successful=successful,
        failed=failed,
        escalated=escalated,
        recovered_amount=total_recovered
    )

@router.post("/simulate-failure", response_model=SimulateFailureResponse)
def simulate_failure(db: Session = Depends(get_db)):
    flag = db.query(DemoFlag).filter(DemoFlag.id == 1).first()
    if not flag:
        flag = DemoFlag(id=1, simulate_failure_active=True)
        db.add(flag)
    else:
        flag.simulate_failure_active = True
    db.commit()
    
    case = db.query(RecoveryCase).filter(RecoveryCase.recovery_status == "pending").first()
    case_id = case.id if case else "NONE"
    
    return SimulateFailureResponse(
        case_id=case_id,
        status="armed",
        message="Simulated gateway failure armed for the next recovery execute." 
    )
