"""Demo control-plane routes.

These routes can seed, reset and perturb the database, so they are triple
guarded: they only exist when DEMO_MODE is explicitly enabled, they are hard
disabled whenever APP_ENV=production, and they optionally require a shared
``X-Demo-Token`` header.
"""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..middleware.rate_limit import limiter
from ..models import (
    AuditLog,
    AuditSeal,
    Customer,
    DemoFlag,
    Execution,
    IdempotencyKey,
    Payment,
    RecoveryCase,
    WebhookEvent,
)
from ..schemas import BatchResponse, SeedResponse, SimulateFailureResponse
from ..services.audit_service import log_event
from ..services.batch_executor import run_batch_recovery
from ..services.metrics_service import invalidate_metrics_cache
from ..services.synthetic_data import generate_synthetic_data

router = APIRouter()


def require_demo_access(request: Request):
    """Single dependency enforcing the demo control-plane guard."""
    if not settings.demo_controls_enabled:
        raise HTTPException(status_code=404, detail="Demo controls are disabled")
    if settings.DEMO_API_TOKEN and not secrets.compare_digest(
        request.headers.get("X-Demo-Token", ""), settings.DEMO_API_TOKEN
    ):
        raise HTTPException(status_code=403, detail="Valid X-Demo-Token header required")


@router.post("/seed", response_model=SeedResponse, dependencies=[Depends(require_demo_access)])
@limiter.limit(settings.RATE_LIMIT_DEMO)
def seed_database(request: Request, db: Session = Depends(get_db)):
    records, cases = generate_synthetic_data(db)
    return SeedResponse(
        created_records=records,
        message=f"Demo dataset seeded with {records} payments and {cases} recovery cases.",
    )


@router.post("/reset", dependencies=[Depends(require_demo_access)])
@limiter.limit(settings.RATE_LIMIT_DEMO)
def reset_database(request: Request, db: Session = Depends(get_db)):
    db.query(AuditLog).delete()
    db.query(AuditSeal).delete()
    db.query(Execution).delete()
    db.query(RecoveryCase).delete()
    db.query(Payment).delete()
    db.query(Customer).delete()
    db.query(DemoFlag).delete()
    db.query(IdempotencyKey).delete()
    db.query(WebhookEvent).delete()
    log_event(
        db,
        case_id=None,
        event_type="demo_reset",
        actor="operator",
        reason="Demo database reset via /api/demo/reset",
    )
    db.commit()
    invalidate_metrics_cache()
    return {"message": "Database reset complete."}


@router.post(
    "/recovery-batch", response_model=BatchResponse, dependencies=[Depends(require_demo_access)]
)
@limiter.limit(settings.RATE_LIMIT_DEMO)
def run_recovery_batch(request: Request, db: Session = Depends(get_db)):
    return run_batch_recovery(db)


@router.post(
    "/simulate-failure",
    response_model=SimulateFailureResponse,
    dependencies=[Depends(require_demo_access)],
)
@limiter.limit(settings.RATE_LIMIT_DEMO)
def simulate_failure(request: Request, db: Session = Depends(get_db)):
    flag = db.query(DemoFlag).filter(DemoFlag.id == 1).first()
    if not flag:
        flag = DemoFlag(id=1, simulate_failure_active=True)
        db.add(flag)
    else:
        flag.simulate_failure_active = True
    db.commit()

    case = db.query(RecoveryCase).filter(RecoveryCase.recovery_status == "pending").first()
    case_id = case.id if case else "NONE"

    log_event(
        db,
        case_id=case.id if case else None,
        event_type="failure_simulation_armed",
        actor="operator",
        reason="Simulated gateway failure armed via UI toggle",
    )
    db.commit()

    return SimulateFailureResponse(
        case_id=case_id,
        status="armed",
        message="Simulated gateway failure armed for the next recovery execute.",
    )
