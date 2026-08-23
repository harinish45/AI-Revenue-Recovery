"""
audit.py — Compliance audit log endpoints
------------------------------------------
GET /api/audit/  — return audit log entries, newest first
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models import AuditLog
from ..schemas import AuditLogOut

router = APIRouter()


@router.get("/", response_model=List[AuditLogOut])
def get_audit_logs(
    limit: int = Query(200, ge=1, le=1000, description="Max log entries to return"),
    case_id: Optional[int] = Query(None, description="Filter by case ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    db: Session = Depends(get_db),
):
    """
    Return compliance audit log entries.

    Optional filters:
      ?case_id=42          — show only logs for a specific case
      ?event_type=LLM_DIAGNOSIS — show only a specific event type

    Standard event types:
      LLM_DIAGNOSIS
      POLICY_CHECK
      EXECUTION_STARTED
      RAZORPAY_API_CALL
      EXECUTION_COMPLETE
      RECOVERY_FAILED
      ESCALATED_TO_HUMAN
    """
    query = db.query(AuditLog).order_by(AuditLog.timestamp.desc())

    if case_id is not None:
        query = query.filter(AuditLog.case_id == case_id)

    if event_type is not None:
        query = query.filter(AuditLog.event_type == event_type.upper())

    logs = query.limit(limit).all()
    return logs
