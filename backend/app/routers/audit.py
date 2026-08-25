from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditLog, AuditSeal
from ..schemas import AuditListResponse, AuditSealVerifyResponse

router = APIRouter()


@router.get("/audit", response_model=AuditListResponse)
def get_audit_logs(
    case_id: Optional[str] = None,
    page: int = Query(1, ge=1, le=10000),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if case_id:
        query = query.filter(AuditLog.case_id == case_id)

    query = query.order_by(AuditLog.timestamp.desc())
    total = query.count()
    logs = query.offset((page - 1) * limit).limit(limit).all()
    seals = {s.audit_id: s for s in db.query(AuditSeal).filter(AuditSeal.audit_id.in_([l.id for l in logs])).all()}

    items = []
    for log in logs:
        seal = seals.get(log.id)
        items.append({
            "id": log.id, "case_id": log.case_id, "event_type": log.event_type,
            "actor": log.actor, "decision": log.decision, "reason": log.reason,
            "action": log.action, "result": log.result, "timestamp": log.timestamp,
            "event_hash": seal.event_hash if seal else None,
            "previous_hash": seal.previous_hash if seal else None,
        })
    return AuditListResponse(items=items, page=page, limit=limit, total=total)


@router.get("/audit/{audit_id}/verify", response_model=AuditSealVerifyResponse)
def verify_audit_seal(audit_id: str, db: Session = Depends(get_db)):
    seal = db.query(AuditSeal).filter(AuditSeal.audit_id == audit_id).first()
    if not seal:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Audit seal not found")
    previous = None
    if seal.previous_hash:
        previous = db.query(AuditSeal).filter(AuditSeal.event_hash == seal.previous_hash).first()
    return AuditSealVerifyResponse(
        audit_id=audit_id,
        chain_verified=seal.previous_hash is None or previous is not None,
        event_hash=seal.event_hash,
        previous_hash=seal.previous_hash,
        case_id=seal.case_id,
    )
