from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditLog
from ..schemas import AuditListResponse

router = APIRouter()


@router.get("/audit", response_model=AuditListResponse)
def get_audit_logs(
    case_id: Optional[str] = None, page: int = Query(1, ge=1, le=10000), limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)
):
    query = db.query(AuditLog)
    if case_id:
        query = query.filter(AuditLog.case_id == case_id)

    query = query.order_by(AuditLog.timestamp.desc())
    total = query.count()
    logs = query.offset((page - 1) * limit).limit(limit).all()

    return AuditListResponse(items=logs, page=page, limit=limit, total=total)
