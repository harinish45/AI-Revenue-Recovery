import uuid
import hashlib
import json
from datetime import datetime

from sqlalchemy.orm import Session

from ..models import AuditLog, AuditSeal


def log_event(
    db: Session,
    case_id: str,
    event_type: str,
    actor: str = "recoverai-agent",
    decision: str = None,
    reason: str = None,
    action: str = None,
    result: str = None,
) -> AuditLog:
    timestamp = datetime.utcnow()
    event_id = f"AUD-{uuid.uuid4().hex[:6].upper()}"
    previous = (
        db.query(AuditSeal).filter(AuditSeal.case_id == case_id)
        .order_by(AuditSeal.created_at.desc()).first()
    )
    payload = {
        "id": event_id, "case_id": case_id, "event_type": event_type,
        "actor": actor, "decision": decision, "reason": reason,
        "action": action, "result": result, "timestamp": timestamp.isoformat(),
        "previous_hash": previous.event_hash if previous else None,
    }
    event_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    log = AuditLog(
        id=event_id,
        case_id=case_id,
        event_type=event_type,
        actor=actor,
        decision=decision,
        reason=reason,
        action=action,
        result=result,
        timestamp=timestamp,
    )
    db.add(log)
    db.add(AuditSeal(audit_id=event_id, case_id=case_id,
                     previous_hash=previous.event_hash if previous else None,
                     event_hash=event_hash, created_at=timestamp))
    return log
