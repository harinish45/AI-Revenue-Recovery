from ..models import AuditLog
from sqlalchemy.orm import Session
from datetime import datetime

def log_event(db: Session, case_id: int, event_type: str, details: dict):
    log = AuditLog(
        case_id=case_id,
        event_type=event_type,
        details=details,
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
