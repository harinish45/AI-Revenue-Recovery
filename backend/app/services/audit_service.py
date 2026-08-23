"""
audit_service.py
----------------
Immutable audit event logger.

Every important system decision is recorded here for compliance
and judge-facing evidence.

Event types:
  LLM_DIAGNOSIS        - AI diagnosis + recommendation produced
  POLICY_CHECK         - Policy engine evaluation result
  EXECUTION_STARTED    - Recovery execution initiated
  RAZORPAY_API_CALL    - Razorpay adapter called (real or simulated)
  EXECUTION_COMPLETE   - Execution finished (success or failure)
  RECOVERY_FAILED      - Recovery attempt failed
  ESCALATED_TO_HUMAN   - Case escalated to human review
"""
from ..models import AuditLog
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional


def log_event(
    db: Session,
    case_id: Optional[int],
    event_type: str,
    details: dict,
    actor: str = "SYSTEM",
    decision: Optional[str] = None,
    action: Optional[str] = None,
    result_summary: Optional[str] = None,
) -> AuditLog:
    """
    Persist an audit event.

    Args:
        db:             Database session
        case_id:        Associated recovery case ID (None for pre-case events)
        event_type:     One of the canonical event type constants
        details:        Arbitrary JSON detail dict
        actor:          Who performed the action (default: SYSTEM)
        decision:       APPROVED / REJECTED / ESCALATED etc.
        action:         What action was taken
        result_summary: Short human-readable outcome

    Returns:
        The persisted AuditLog instance.
    """
    log = AuditLog(
        case_id=case_id,
        event_type=event_type,
        actor=actor,
        decision=decision,
        action=action,
        result_summary=result_summary,
        details=details,
        timestamp=datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
