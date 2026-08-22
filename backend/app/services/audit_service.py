from sqlalchemy.orm import Session
from app.models import AuditLog
from typing import Dict, Any

def log_action(db: Session, case_id: int, action: str, details: Dict[str, Any]):
    log = AuditLog(
        recovery_case_id=case_id,
        action=action,
        details=details
    )
    db.add(log)
    db.commit()
    return log
