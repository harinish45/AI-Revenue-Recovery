"""Dunning management and notification sequence API routes."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DunningNotification, RecoveryCase
from ..schemas import (
    DunningNotificationOut,
    DunningStateOut,
    DunningTransitionRequest,
    NotificationPreviewRequest,
    NotificationSendRequest,
)
from ..security.auth import require_operator, require_readonly
from ..services.dunning_engine import (
    DunningState,
    can_transition,
    transition_dunning_state,
)
from ..services.dunning_notifications import (
    NotificationTemplate,
    render_template,
    send_dunning_notification,
)

router = APIRouter()


@router.get(
    "/dunning/{case_id}/state",
    response_model=DunningStateOut,
    dependencies=[Depends(require_readonly)],
)
def get_dunning_state(case_id: str, db: Session = Depends(get_db)):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Recovery case not found")

    current_state = case.dunning_state or "pending"
    is_terminal = current_state in (
        DunningState.RECOVERED.value,
        DunningState.CHURNED.value,
        DunningState.HARD_DECLINED.value,
        DunningState.SKIPPED.value,
    )

    return DunningStateOut(
        case_id=case.id,
        current_state=current_state,
        failure_category=case.failure_category,
        next_retry_at=case.next_retry_at,
        retry_count=case.retry_count or 0,
        max_retries=case.max_retries or 2,
        recovery_probability=case.recovery_probability,
        churn_risk_score=case.churn_risk_score,
        is_terminal=is_terminal,
    )


@router.post(
    "/dunning/{case_id}/transition",
    response_model=DunningStateOut,
    dependencies=[Depends(require_operator)],
)
def transition_case_state(
    case_id: str,
    body: DunningTransitionRequest,
    db: Session = Depends(get_db),
):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).with_for_update().first()
    if not case:
        raise HTTPException(status_code=404, detail="Recovery case not found")

    try:
        target = DunningState(body.target_state)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid target state: {body.target_state}"
        ) from exc

    current_state = case.dunning_state or "pending"
    if not can_transition(current_state, target):
        raise HTTPException(
            status_code=400,
            detail=f"Transition from {current_state} to {target.value} is not permitted",
        )

    transition_dunning_state(
        db=db,
        case=case,
        target_state=target,
        reason=body.reason,
        actor="operator",
    )
    db.commit()

    return DunningStateOut(
        case_id=case.id,
        current_state=case.dunning_state,
        failure_category=case.failure_category,
        next_retry_at=case.next_retry_at,
        retry_count=case.retry_count or 0,
        max_retries=case.max_retries or 2,
        recovery_probability=case.recovery_probability,
        churn_risk_score=case.churn_risk_score,
        is_terminal=case.dunning_state
        in (
            DunningState.RECOVERED.value,
            DunningState.CHURNED.value,
            DunningState.HARD_DECLINED.value,
            DunningState.SKIPPED.value,
        ),
    )


@router.post(
    "/dunning/{case_id}/notifications",
    response_model=DunningNotificationOut,
    dependencies=[Depends(require_operator)],
)
def send_notification(
    case_id: str,
    body: NotificationSendRequest,
    db: Session = Depends(get_db),
):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Recovery case not found")

    try:
        tmpl = NotificationTemplate(body.template)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail=f"Unsupported template: {body.template}"
        ) from exc

    notif = send_dunning_notification(
        db=db,
        case=case,
        template=tmpl,
        sequence_step=body.sequence_step,
        locale=body.locale,
        channel=body.channel or "email",
    )
    db.commit()
    db.refresh(notif)
    return notif


@router.get(
    "/dunning/{case_id}/notifications",
    response_model=List[DunningNotificationOut],
    dependencies=[Depends(require_readonly)],
)
def list_case_notifications(case_id: str, db: Session = Depends(get_db)):
    case = db.query(RecoveryCase).filter(RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Recovery case not found")

    notifs = (
        db.query(DunningNotification)
        .filter(DunningNotification.case_id == case_id)
        .order_by(DunningNotification.sent_at.asc())
        .all()
    )
    return notifs


@router.post("/dunning/notifications/preview", dependencies=[Depends(require_readonly)])
def preview_notification(body: NotificationPreviewRequest):
    try:
        tmpl = NotificationTemplate(body.template)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail=f"Unsupported template: {body.template}"
        ) from exc

    rendered = render_template(tmpl, body.locale, body.context)
    return {
        "template": body.template,
        "locale": body.locale,
        "subject": rendered.subject,
        "body": rendered.body,
    }
