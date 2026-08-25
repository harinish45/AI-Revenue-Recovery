from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..middleware.rate_limit import limiter
from ..models import RecoveryCase
from ..schemas import ExecuteRequest, ExecuteResponse
from ..services.recovery_executor import execute_recovery

router = APIRouter()


def _execute_case(db: Session, case_id: str, idempotency_key: Optional[str]) -> dict:
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return execute_recovery(db, case, idempotency_key)


@router.post("/cases/{case_id}/execute", response_model=ExecuteResponse)
@limiter.limit(settings.RATE_LIMIT_EXECUTE)
def execute_case_path(
    request: Request,
    case_id: str,
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
