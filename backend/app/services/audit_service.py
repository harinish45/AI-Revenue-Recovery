from ..models import AuditLog
from sqlalchemy.orm import Session
from datetime import datetime, timezone

def log_event(
    db: Session, 
    case_id: int, 
    event_type: str, 
    details: dict = None
) -> AuditLog:
    if details is None:
        details = {}
        
    log = AuditLog(
        case_id=case_id,
        event_type=event_type,
        details=details,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
