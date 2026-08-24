from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..middleware.rate_limit import limiter
from ..models import RecoveryCase
from ..schemas import VoiceEventRequest, VoiceEventResponse
from ..services.audit_service import log_event

router = APIRouter()


@router.post("/cases/{case_id}/voice-events", response_model=VoiceEventResponse)
@limiter.limit(settings.RATE_LIMIT_DEMO)
def record_voice_event(
    request: Request, case_id: str, body: VoiceEventRequest, db: Session = Depends(get_db)
):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    audit = log_event(
        db,
        case_id,
        body.event_type,
        actor="voice_agent",
        decision=body.intent,
        reason=body.transcript,
    )
    db.commit()

    return VoiceEventResponse(audit_event_id=audit.id, case_id=case_id, event_type=body.event_type)
