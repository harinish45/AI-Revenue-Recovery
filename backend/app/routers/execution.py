from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..middleware.rate_limit import limiter
from ..models import RecoveryCase
from ..schemas import ExecuteRequest, ExecuteResponse
from ..security.auth import require_operator
from ..services.payment_confirmation import confirm_provider_payment
from ..services.recovery_executor import execute_recovery

router = APIRouter(dependencies=[Depends(require_operator)])


def _execute_case(db: Session, case_id: str, idempotency_key: Optional[str]) -> dict:
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")
    idempotency_key = idempotency_key.strip()
    if len(idempotency_key) > 200:
        raise HTTPException(status_code=400, detail="Idempotency-Key is too long")
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return execute_recovery(db, case, idempotency_key)


@router.post("/cases/{case_id}/execute", response_model=ExecuteResponse)
@limiter.limit(settings.RATE_LIMIT_EXECUTE)
def execute_case_path(
    request: Request,
    case_id: str = Path(..., min_length=1, max_length=64, pattern=r"^RC-[A-Za-z0-9_-]+$"),
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    return _execute_case(db, case_id, idempotency_key)


@router.post("/execute", response_model=ExecuteResponse)
@limiter.limit(settings.RATE_LIMIT_EXECUTE)
def execute_case_body(
    request: Request,
    req: ExecuteRequest,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    return _execute_case(db, req.case_id, idempotency_key)


@router.post("/cases/{case_id}/confirm-payment", response_model=ExecuteResponse)
@limiter.limit(settings.RATE_LIMIT_EXECUTE)
def confirm_payment(
    request: Request,
    case_id: str = Path(..., min_length=1, max_length=64, pattern=r"^RC-[A-Za-z0-9_-]+$"),
    db: Session = Depends(get_db),
):
    """Operator/provider-confirmed payment: the ONLY way an awaiting_payment
    case becomes counted revenue."""
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    result = confirm_provider_payment(db, case, actor="operator")
    if result is None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Case is {case.recovery_status}; only an 'awaiting_payment' case can "
                "be confirmed by a provider payment event"
            ),
        )
    db.commit()
    return result
