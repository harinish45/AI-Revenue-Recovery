"""
demo.py — Demo control endpoints
---------------------------------
Provides endpoints for seeding data, resetting, running batch recovery,
and arming failure simulation.

Routes:
  POST /api/demo/seed              — Seed 100 deterministic payments + cases
  POST /api/demo/reset             — Clear all data
  POST /api/demo/recovery-batch    — Run batch recovery on all OPEN cases
  POST /api/demo/simulate-failure  — Arm failure simulation for next execution
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Payment, RecoveryCase, Execution, AuditLog
from ..services.synthetic_data import generate_synthetic_payments
from ..services.decision_engine import diagnose_and_recommend
from ..services.recovery_executor import execute_recovery
from ..services.failure_state import arm_failure, reset_failure, is_armed
from ..services.metrics_service import get_metrics
from ..schemas import OkResponse, BatchRecoveryResult

router = APIRouter()


@router.post("/seed", response_model=OkResponse)
def seed_database(db: Session = Depends(get_db)):
    """
    Seed the database with 100 deterministic demo payments and recovery cases.
    Clears all existing data first.
    """
    # Clear in dependency order
    db.query(AuditLog).delete()
    db.query(Execution).delete()
    db.query(RecoveryCase).delete()
    db.query(Payment).delete()
    db.commit()

    # Reset failure simulation state
    reset_failure()

    # Generate deterministic payments (seed=42)
    count = generate_synthetic_payments(db, 100)

    # Create recovery cases with AI diagnosis
    payments = db.query(Payment).all()
    for p in payments:
        # First create case (without case_id) to get the ID
        case = RecoveryCase(
            payment_id=p.id,
            diagnosis="Pending",
            recommended_action="PENDING",
            confidence=0.0,
            evidence=[],
            risk_level="MEDIUM",
        )
        db.add(case)
        db.flush()  # Get case.id without committing

        # Now diagnose with proper case_id linkage
        result = diagnose_and_recommend(db, p, case_id=case.id)

        # Update case with diagnosis
        case.diagnosis = result["diagnosis"]
        case.recommended_action = result["recommended_action"]
        case.confidence = result["confidence"]
        case.evidence = result["evidence"]
        case.risk_level = result["risk_level"]

    db.commit()

    return OkResponse(
        message=f"Seeded {count} payments and {count} recovery cases successfully.",
        detail={"count": count},
    )


@router.post("/reset", response_model=OkResponse)
def reset_database(db: Session = Depends(get_db)):
    """Clear all demo data and reset failure simulation state."""
    db.query(AuditLog).delete()
    db.query(Execution).delete()
    db.query(RecoveryCase).delete()
    db.query(Payment).delete()
    db.commit()
    reset_failure()
    return OkResponse(message="Database reset complete. All demo data cleared.")


@router.post("/recovery-batch", response_model=BatchRecoveryResult)
def run_batch_recovery(db: Session = Depends(get_db)):
    """
    Run automated batch recovery on all OPEN cases.

    Iterates every OPEN case, applies policy check, and executes recovery.
    Returns aggregate statistics.
    """
    open_cases = (
        db.query(RecoveryCase)
        .filter(RecoveryCase.status == "OPEN")
        .all()
    )

    total_cases = len(open_cases)
    attempted = 0
    successful = 0
    failed_count = 0
    escalated = 0
    amount_recovered = 0.0

    # Compute amount_at_risk before execution
    from sqlalchemy import func
    at_risk_payments = (
        db.query(func.sum(Payment.amount))
        .filter(Payment.status.in_(["failed", "abandoned"]))
        .scalar()
        or 0.0
    )

    for case in open_cases:
        attempted += 1
        result = execute_recovery(db, case)

        # Refresh case from DB
        db.refresh(case)

        if case.status == "RECOVERED":
            successful += 1
            amount_recovered += result.get("amount_recovered", 0.0)
        elif case.status in ("ESCALATED", "NEEDS_HUMAN_REVIEW"):
            escalated += 1
        else:
            failed_count += 1

    recovery_rate = (
        (amount_recovered / at_risk_payments * 100) if at_risk_payments > 0 else 0.0
    )

    return BatchRecoveryResult(
        total_cases=total_cases,
        attempted=attempted,
        successful=successful,
        failed=failed_count,
        escalated=escalated,
        amount_at_risk=round(at_risk_payments, 2),
        amount_recovered=round(amount_recovered, 2),
        recovery_rate_percent=round(recovery_rate, 2),
    )


@router.post("/simulate-failure", response_model=OkResponse)
def simulate_failure():
    """
    Arm the failure simulation flag.

    The next recovery execution will produce a controlled gateway failure
    and escalate the case to NEEDS_HUMAN_REVIEW.
    After one use, the flag automatically resets.
    """
    arm_failure()
    return OkResponse(
        message="Failure simulation armed. Next recovery execution will trigger gateway failure.",
        detail={"failure_armed": True},
    )


@router.get("/failure-status")
def failure_status():
    """Check whether failure simulation is currently armed."""
    return {"failure_armed": is_armed()}
