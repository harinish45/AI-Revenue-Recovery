from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditLog, AuditSeal
from ..schemas import AuditListResponse, AuditSealVerifyResponse
from ..services.audit_service import _compute_event_hash, verify_chain

router = APIRouter()


def _sealed_payload(log: AuditLog, seal: AuditSeal) -> dict:
    return {
        "id": log.id,
        "case_id": log.case_id,
        "event_type": log.event_type,
        "actor": log.actor,
        "decision": log.decision,
        "reason": log.reason,
        "action": log.action,
        "result": log.result,
        "timestamp": log.timestamp.isoformat(),
        "sequence": seal.sequence,
        "previous_hash": seal.previous_hash,
    }


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

    # Order by the monotonic seal sequence (timestamp ordering can collide).
    query = query.outerjoin(AuditSeal, AuditSeal.audit_id == AuditLog.id).order_by(
        AuditSeal.sequence.desc()
    )
    total = query.count()
    logs = query.offset((page - 1) * limit).limit(limit).all()
    seals = {
        s.audit_id: s
        for s in db.query(AuditSeal).filter(AuditSeal.audit_id.in_([log.id for log in logs])).all()
    }

    items = []
    for log in logs:
        seal = seals.get(log.id)
        items.append(
            {
                "id": log.id,
                "case_id": log.case_id,
                "event_type": log.event_type,
                "actor": log.actor,
                "decision": log.decision,
                "reason": log.reason,
                "action": log.action,
                "result": log.result,
                "timestamp": log.timestamp,
                "event_hash": seal.event_hash if seal else None,
                "previous_hash": seal.previous_hash if seal else None,
                "sequence": seal.sequence if seal else None,
            }
        )
    return AuditListResponse(items=items, page=page, limit=limit, total=total)


@router.get("/audit/chain/verify")
def verify_audit_chain(case_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Recursively verify the entire tamper-evident hash chain."""
    return verify_chain(db, case_id)


@router.get("/audit/{audit_id}/verify", response_model=AuditSealVerifyResponse)
def verify_audit_seal(audit_id: str, db: Session = Depends(get_db)):
    seal = db.query(AuditSeal).filter(AuditSeal.audit_id == audit_id).first()
    if not seal:
        raise HTTPException(status_code=404, detail="Audit seal not found")
    log = db.query(AuditLog).filter(AuditLog.id == audit_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Audit event not found")
    computed_hash = _compute_event_hash(_sealed_payload(log, seal))
    previous = None
    if seal.previous_hash:
        previous = db.query(AuditSeal).filter(AuditSeal.event_hash == seal.previous_hash).first()
    return AuditSealVerifyResponse(
        audit_id=audit_id,
        chain_verified=computed_hash == seal.event_hash
        and (seal.previous_hash is None or previous is not None),
        event_hash=seal.event_hash,
        previous_hash=seal.previous_hash,
        case_id=seal.case_id,
    )
