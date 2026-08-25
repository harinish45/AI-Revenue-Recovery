import hashlib
import hmac
import json
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..schemas import WebhookResponse
from ..services.audit_service import log_event

router = APIRouter()


@router.post("/webhooks/razorpay", response_model=WebhookResponse)
def ingest_razorpay_webhook(
    request: Request,
    payload: dict,
    db: Session = Depends(get_db),
    x_razorpay_signature: str | None = Header(default=None),
):
    """Safe ingestion seam: validate a configured HMAC, then audit the event.

    A production deployment should enqueue the event for asynchronous
    processing. This demo intentionally does not mutate payment state here.
    """
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    if settings.WEBHOOK_SECRET:
        expected = hmac.new(settings.WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
        if not x_razorpay_signature or not hmac.compare_digest(expected, x_razorpay_signature):
            raise HTTPException(status_code=401, detail="Invalid Razorpay webhook signature")
    event_id = str(payload.get("id") or f"wh_{uuid4().hex[:12]}")
    log_event(db, None, "razorpay_webhook_received", actor="razorpay_webhook", action="enqueue", reason=event_id)
    db.commit()
    return WebhookResponse(accepted=True, event_id=event_id, message="Webhook accepted for async processing.")
