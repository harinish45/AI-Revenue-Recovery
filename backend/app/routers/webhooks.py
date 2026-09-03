"""Provider webhook ingestion with replay, size, schema and signature guards.

Only signed, fresh, allow-listed Razorpay events are accepted. Confirmed
payment events (payment.captured / payment_link.paid) are the ONLY path that
turns an ``awaiting_payment`` case into counted revenue.
"""

import hashlib
import hmac
import json
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import RecoveryCase, WebhookEvent
from ..schemas import WebhookResponse
from ..services.audit_service import log_event
from ..services.payment_confirmation import confirm_provider_payment
from ..utils.time import utcnow

router = APIRouter()

# Payloads that confirm money movement for a tracked recovery case.
CONFIRMATION_EVENTS = {"payment.captured", "payment_link.paid"}


def _signature_valid(raw: bytes, signature: str | None) -> bool:
    if not settings.WEBHOOK_SECRET:
        return False
    expected = hmac.new(settings.WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return bool(signature) and hmac.compare_digest(expected, signature)


@router.post("/webhooks/razorpay", response_model=WebhookResponse)
async def ingest_razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_razorpay_signature: str | None = Header(default=None),
):
    raw = await request.body()

    # Guard 1: bounded request size.
    if len(raw) > settings.WEBHOOK_MAX_BODY_BYTES:
        raise HTTPException(
            status_code=413, detail="Webhook payload exceeds the maximum allowed size"
        )

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Webhook body must be valid JSON") from exc

    # Guard 2: strict object shape.
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Webhook body must be a JSON object")

    # Guard 3: signature is mandatory unless the provider is explicitly in
    # simulation mode with no secret configured.
    if settings.WEBHOOK_SECRET:
        if not _signature_valid(raw, x_razorpay_signature):
            raise HTTPException(status_code=401, detail="Invalid Razorpay webhook signature")
    elif not settings.RAZORPAY_SIMULATE:
        raise HTTPException(status_code=503, detail="Webhook verification is not configured")

    # Guard 4: allow-listed event types only.
    event_type = str(payload.get("event") or "")
    if event_type not in settings.WEBHOOK_ALLOWED_EVENTS:
        raise HTTPException(
            status_code=400, detail=f"Unsupported webhook event type: {event_type or '<missing>'}"
        )

    # Guard 5: a provider event id is required so replays deduplicate.
    event_id = str(payload.get("id") or "")
    if not event_id:
        raise HTTPException(
            status_code=400, detail="Webhook payload must include a provider event id"
        )

    # Guard 6: reject stale events (replay protection).
    event_ts = payload.get("timestamp") or request.headers.get("X-Razorpay-Event-Timestamp")
    if event_ts is not None:
        try:
            event_time = datetime_from_epoch_or_iso(event_ts)
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=400, detail="Invalid webhook timestamp") from exc
        if event_time is not None and (utcnow().replace(tzinfo=None) - event_time) > timedelta(
            seconds=settings.WEBHOOK_MAX_AGE_SECONDS
        ):
            raise HTTPException(status_code=400, detail="Webhook event is stale and was rejected")

    if db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first():
        return WebhookResponse(
            accepted=True, event_id=event_id, message="Webhook already accepted; duplicate ignored."
        )

    db.add(WebhookEvent(event_id=event_id))
    log_event(
        db,
        None,
        "razorpay_webhook_received",
        actor="razorpay_webhook",
        action=event_type,
        reason=event_id,
    )

    # Provider-confirmed recovery: the only path that counts revenue for an
    # intervention that merely *requested* money.
    if event_type in CONFIRMATION_EVENTS:
        provider_payment_id = str(
            (payload.get("payload") or {}).get("payment", {}).get("id")
            or payload.get("payment_id")
            or ""
        )
        if provider_payment_id:
            # confirm_provider_payment() re-fetches and locks the case row
            # itself, so a provider retry racing an operator's manual
            # confirm-payment call still can't double-count revenue.
            case = (
                db.query(RecoveryCase)
                .filter(RecoveryCase.payment_id == provider_payment_id)
                .filter(RecoveryCase.recovery_status == "awaiting_payment")
                .first()
            )
            if case:
                confirm_provider_payment(db, case, actor="razorpay_webhook")

    db.commit()
    return WebhookResponse(
        accepted=True, event_id=event_id, message="Webhook accepted for async processing."
    )


def datetime_from_epoch_or_iso(value):
    """Accept unix epoch seconds or an ISO-8601 timestamp; return naive UTC."""
    from datetime import datetime, timezone

    if isinstance(value, (int, float)):
        result = datetime.utcfromtimestamp(float(value))
    elif isinstance(value, str) and value.isdigit():
        result = datetime.utcfromtimestamp(float(value))
    else:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if result.tzinfo is not None:
            result = result.astimezone(timezone.utc).replace(tzinfo=None)
    return result
