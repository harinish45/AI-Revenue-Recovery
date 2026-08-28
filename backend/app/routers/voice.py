"""Voice agent events.

A recorded payment promise is only accepted with EXPLICIT consent
(``consent_confirmed`` must be ``true``). Transcript and intent sizes are
bounded by the request schema.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..middleware.rate_limit import limiter
from ..models import RecoveryCase
from ..schemas import VoiceEventRequest, VoiceEventResponse
from ..services.audit_service import log_event
from ..services.policy_engine import TERMINAL_STATES

router = APIRouter()


@router.post("/cases/{case_id}/voice-events", response_model=VoiceEventResponse)
@limiter.limit(settings.RATE_LIMIT_DEMO)
def record_voice_event(
    request: Request, case_id: str, body: VoiceEventRequest, db: Session = Depends(get_db)
):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if str(case.recovery_status or "").lower() in TERMINAL_STATES:
        raise HTTPException(
            status_code=409,
            detail=f"Case is already {case.recovery_status}",
        )

    # A payment promise may ONLY be recorded with explicit, affirmative consent.
    if body.event_type == "voice_promise_captured" and body.consent_confirmed is not True:
        raise HTTPException(
            status_code=400,
            detail="A payment promise requires explicit consent (consent_confirmed=true)",
        )

    decision = body.intent or "VOICE_INTERACTION"
    metadata = []
    if body.language:
        metadata.append(f"language={body.language}")
    if body.confidence is not None:
        metadata.append(f"confidence={body.confidence:.2f}")
    reason = body.transcript
    if metadata:
        reason = "; ".join(filter(None, [reason, "(" + ", ".join(metadata) + ")"]))
    audit = log_event(
        db,
        case_id,
        body.event_type,
        actor="voice_agent",
        decision=decision,
        action="promise_capture" if body.event_type == "voice_promise_captured" else "voice_interaction",
        reason=reason,
    )
    db.commit()

    return VoiceEventResponse(audit_event_id=audit.id, case_id=case_id, event_type=body.event_type)
