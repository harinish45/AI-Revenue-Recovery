"""Voice agent events.

A recorded payment promise is only accepted with EXPLICIT consent
(``consent_confirmed`` must be ``true``). Transcript and intent sizes are
bounded by the request schema.
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..middleware.rate_limit import limiter
from ..models import RecoveryCase
from ..schemas import VoiceEventRequest, VoiceEventResponse
from ..security.auth import require_operator
from ..services.audit_service import log_event
from ..services.policy_engine import TERMINAL_STATES

router = APIRouter(dependencies=[Depends(require_operator)])


@router.post("/cases/{case_id}/voice-events", response_model=VoiceEventResponse)
@limiter.limit(settings.RATE_LIMIT_DEMO)
def record_voice_event(
    request: Request,
    case_id: str = Path(..., min_length=1, max_length=64, pattern=r"^RC-[A-Za-z0-9_-]+$"),
    body: VoiceEventRequest = ...,
    db: Session = Depends(get_db),
):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    recovery_status = str(case.recovery_status or "").lower()
    # Human-review and blocked cases are intentionally available in the
    # cockpit for a compliant operator follow-up.  They are terminal for the
    # automated recovery policy, but not terminal for audit-only voice work.
    voice_follow_up_states = {"needs_human_review", "blocked"}
    if recovery_status in TERMINAL_STATES and recovery_status not in voice_follow_up_states:
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

    # A completed operator conversation becomes a closed CRM case. Escalation
    # and dispute outcomes remain in human review so they are not falsely
    # presented as resolved.
    if body.event_type == "voice_call_ended":
        if body.intent in {"REQUEST_HUMAN", "DISPUTE_RAISED"}:
            case.recovery_status = "needs_human_review"
        elif recovery_status not in {"recovered", "skipped"}:
            case.recovery_status = "closed"

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
        action="promise_capture"
        if body.event_type == "voice_promise_captured"
        else "voice_interaction",
        reason=reason,
    )
    db.commit()

    return VoiceEventResponse(audit_event_id=audit.id, case_id=case_id, event_type=body.event_type)
