from ..models import AuditLog
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

def log_event(
    db: Session, 
    case_id: str, 
    event_type: str, 
    actor: str = "recoverai-agent",
    decision: str = None, 
    reason: str = None, 
    action: str = None, 
    result: str = None
) -> AuditLog:
    log = AuditLog(
        id=f"AUD-{uuid.uuid4().hex[:6].upper()}",
        case_id=case_id,
        event_type=event_type,
        actor=actor,
        decision=decision,
        reason=reason,
        action=action,
        result=result,
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
