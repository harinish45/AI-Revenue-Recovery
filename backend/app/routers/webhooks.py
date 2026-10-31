"""Provider webhook ingestion with replay, size, schema and signature guards.

Accepts and verifies webhook events from:
- Razorpay
- Stripe
- Paddle
- Braintree

Supports failed payment ingestion, automated dunning initialization,
churn risk scoring, dispute tracking, and payment confirmation.
"""

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Customer, Payment, RecoveryCase, WebhookEvent
from ..schemas import WebhookResponse
from ..services.audit_service import log_event
from ..services.churn_scoring import score_case
from ..services.dunning_engine import (
    DeclineCategory,
    DunningState,
    classify_decline,
    evaluate_initial_dunning_flow,
    transition_dunning_state,
)
from ..services.dunning_notifications import (
    NotificationTemplate,
    send_dunning_notification,
)
from ..services.payment_confirmation import confirm_provider_payment
from ..utils.time import utcnow

logger = logging.getLogger("recoverai.webhooks")

router = APIRouter()

RAZORPAY_CONFIRMATION_EVENTS = {"payment.captured", "payment_link.paid"}
STRIPE_CONFIRMATION_EVENTS = {
    "invoice.payment_succeeded",
    "payment_intent.succeeded",
    "charge.succeeded",
}
PADDLE_CONFIRMATION_EVENTS = {"subscription_payment_succeeded", "payment_succeeded"}
BRAINTREE_CONFIRMATION_EVENTS = {"subscription_charged_successfully", "transaction_settled"}


def datetime_from_epoch_or_iso(value: Any) -> datetime:
    """Accept unix epoch seconds or an ISO-8601 timestamp; return naive UTC."""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc).replace(tzinfo=None)
    if isinstance(value, str) and value.isdigit():
        return datetime.fromtimestamp(float(value), tz=timezone.utc).replace(tzinfo=None)
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is not None:
        result = result.astimezone(timezone.utc).replace(tzinfo=None)
    return result


def _verify_razorpay_signature(raw: bytes, signature: Optional[str]) -> bool:
    if not settings.WEBHOOK_SECRET:
        return False
    expected = hmac.new(settings.WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return bool(signature) and hmac.compare_digest(expected, signature)


def _verify_stripe_signature(raw: bytes, signature_header: Optional[str]) -> bool:
    """Validate Stripe signature header (t=timestamp,v1=signature)."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        return False
    if not signature_header:
        return False

    elements = dict(item.split("=", 1) for item in signature_header.split(",") if "=" in item)
    timestamp = elements.get("t")
    signature = elements.get("v1")
    if not timestamp or not signature:
        return False

    try:
        ts_val = int(timestamp)
        now_val = int(utcnow().timestamp())
        if abs(now_val - ts_val) > settings.WEBHOOK_MAX_AGE_SECONDS:
            return False
    except ValueError:
        return False

    signed_payload = f"{timestamp}.{raw.decode('utf-8')}".encode("utf-8")
    expected = hmac.new(
        settings.STRIPE_WEBHOOK_SECRET.encode(), signed_payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _verify_paddle_signature(raw: bytes, signature: Optional[str]) -> bool:
    """Validate Paddle webhook signature."""
    if not settings.PADDLE_WEBHOOK_SECRET:
        return False
    if not signature:
        return False
    expected = hmac.new(settings.PADDLE_WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _verify_braintree_signature(signature: Optional[str], payload: Optional[str]) -> bool:
    """Validate Braintree webhook signature."""
    if not settings.BRAINTREE_WEBHOOK_SECRET:
        return False
    if not signature or not payload:
        return False
    expected = hmac.new(
        settings.BRAINTREE_WEBHOOK_SECRET.encode(), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# =========================================================================
# Razorpay Webhook Endpoint (Existing & Compatible)
# =========================================================================


@router.post("/webhooks/razorpay", response_model=WebhookResponse)
async def ingest_razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_razorpay_signature: str | None = Header(default=None),
    x_razorpay_event_id: str | None = Header(default=None),
):
    raw = await request.body()
    if len(raw) > settings.WEBHOOK_MAX_BODY_BYTES:
        raise HTTPException(
            status_code=413, detail="Webhook payload exceeds the maximum allowed size"
        )

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Webhook body must be valid JSON") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Webhook body must be a JSON object")

    if settings.WEBHOOK_SECRET:
        if not _verify_razorpay_signature(raw, x_razorpay_signature):
            raise HTTPException(status_code=401, detail="Invalid Razorpay webhook signature")
    elif not settings.RAZORPAY_SIMULATE:
        raise HTTPException(status_code=503, detail="Webhook verification is not configured")

    event_type = str(payload.get("event") or "")
    if event_type not in settings.WEBHOOK_ALLOWED_EVENTS:
        raise HTTPException(
            status_code=400, detail=f"Unsupported webhook event type: {event_type or '<missing>'}"
        )

    event_id = str(x_razorpay_event_id or payload.get("id") or "")
    if not event_id:
        raise HTTPException(
            status_code=400, detail="Webhook payload must include a provider event id"
        )

    event_ts = payload.get("created_at") or payload.get("timestamp")
    if event_ts is not None:
        try:
            event_time = datetime_from_epoch_or_iso(event_ts)
        except (ValueError, TypeError, OverflowError) as exc:
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

    if event_type in RAZORPAY_CONFIRMATION_EVENTS:
        payment_payload = (payload.get("payload") or {}).get("payment") or {}
        provider_payment_id = str(
            (payment_payload.get("entity") or {}).get("id")
            or payment_payload.get("id")
            or payload.get("payment_id")
            or ""
        )
        if provider_payment_id:
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


# =========================================================================
# Stripe Webhook Endpoint
# =========================================================================


@router.post("/webhooks/stripe", response_model=WebhookResponse)
async def ingest_stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: Optional[str] = Header(default=None),
):
    raw = await request.body()
    if len(raw) > settings.WEBHOOK_MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Webhook payload exceeds allowed size")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Webhook body must be valid JSON") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Webhook body must be a JSON object")

    if settings.STRIPE_WEBHOOK_SECRET:
        if not _verify_stripe_signature(raw, stripe_signature):
            raise HTTPException(status_code=401, detail="Invalid Stripe webhook signature")
    elif not settings.STRIPE_SIMULATE:
        raise HTTPException(status_code=503, detail="Stripe webhook verification is not configured")

    event_id = str(payload.get("id") or "")
    if not event_id:
        raise HTTPException(status_code=400, detail="Missing Stripe event id")

    event_type = str(payload.get("type") or payload.get("event") or "")
    event_ts = payload.get("created") or payload.get("timestamp")
    if event_ts:
        try:
            event_time = datetime_from_epoch_or_iso(event_ts)
            if (utcnow().replace(tzinfo=None) - event_time) > timedelta(
                seconds=settings.WEBHOOK_MAX_AGE_SECONDS
            ):
                raise HTTPException(status_code=400, detail="Stripe webhook event is stale")
        except (ValueError, TypeError, OverflowError) as exc:
            raise HTTPException(status_code=400, detail="Invalid webhook timestamp") from exc

    if db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first():
        return WebhookResponse(
            accepted=True, event_id=event_id, message="Stripe webhook duplicate ignored."
        )

    db.add(WebhookEvent(event_id=event_id))
    log_event(
        db,
        None,
        "stripe_webhook_received",
        actor="stripe_webhook",
        action=event_type,
        reason=event_id,
    )

    data_obj = (payload.get("data") or {}).get("object") or payload

    # Handle Payment / Invoice Success (Confirmation)
    if event_type in STRIPE_CONFIRMATION_EVENTS:
        stripe_payment_id = str(data_obj.get("payment_intent") or data_obj.get("id") or "")
        case = (
            db.query(RecoveryCase)
            .filter(RecoveryCase.payment_id == stripe_payment_id)
            .filter(RecoveryCase.recovery_status.in_(["awaiting_payment", "pending"]))
            .first()
        )
        if case:
            confirm_provider_payment(db, case, actor="stripe_webhook")
            transition_dunning_state(
                db,
                case,
                DunningState.RECOVERED,
                "Stripe confirmed payment recovery",
                actor="stripe_webhook",
            )

    # Handle Payment / Invoice Failure
    elif event_type in ("invoice.payment_failed", "charge.failed"):
        cust_id = str(data_obj.get("customer") or f"cust_{uuid.uuid4().hex[:8]}")
        cust_email = str(data_obj.get("customer_email") or "customer@example.com")
        cust_name = str(data_obj.get("customer_name") or "Stripe Subscriber")

        customer = db.query(Customer).filter(Customer.id == cust_id).first()
        if not customer:
            customer = Customer(id=cust_id, name=cust_name, email=cust_email)
            db.add(customer)

        amount = float(data_obj.get("amount_due") or data_obj.get("amount") or 120000) / 100.0
        currency = str(data_obj.get("currency") or "USD").upper()
        stripe_payment_id = str(
            data_obj.get("payment_intent") or data_obj.get("id") or f"pi_{uuid.uuid4().hex[:12]}"
        )

        outcome = data_obj.get("outcome") or {}
        payment_method_details = (data_obj.get("payment_method_details") or {}).get("card") or {}
        card_brand = payment_method_details.get("brand") or "visa"
        failure_code = outcome.get("reason") or data_obj.get("failure_code") or "insufficient_funds"
        failure_reason = (
            outcome.get("seller_message")
            or data_obj.get("failure_message")
            or "Your card has insufficient funds."
        )

        payment = Payment(
            id=stripe_payment_id,
            customer_id=customer.id,
            amount=amount,
            currency=currency,
            status="failed",
            gateway="stripe",
            failure_code=failure_code,
            failure_reason=failure_reason,
            card_brand=card_brand,
            timestamp=utcnow(),
        )
        db.add(payment)

        decline_cat = classify_decline(failure_code, failure_reason)
        case = RecoveryCase(
            id=f"RC-{uuid.uuid4().hex[:6].upper()}",
            payment_id=payment.id,
            customer_id=customer.id,
            customer_name=customer.name,
            amount_at_risk=amount,
            risk_level="medium",
            failure_category=decline_cat.value,
            recommended_action="smart_retry"
            if decline_cat != DeclineCategory.EXPIRED_CARD
            else "customer_reminder",
            reason=failure_reason,
            gateway="stripe",
            evidence={"gateway": "stripe", "decline_code": failure_code, "brand": card_brand},
            policy_checks={"allowed": True},
        )
        db.add(case)
        db.flush()

        score_case(db, case)
        state, next_retry, _ = evaluate_initial_dunning_flow(db, case, payment)

        # Trigger notification sequence
        if state == DunningState.CARD_UPDATE_REQUESTED:
            send_dunning_notification(
                db, case, NotificationTemplate.CARD_EXPIRATION, sequence_step=1
            )
        else:
            send_dunning_notification(db, case, NotificationTemplate.GRACE_PERIOD, sequence_step=1)

    # Handle Charge Dispute / Chargeback
    elif event_type == "charge.dispute.created":
        charge_id = str(data_obj.get("charge") or "")
        case = db.query(RecoveryCase).filter(RecoveryCase.payment_id == charge_id).first()
        if case:
            transition_dunning_state(
                db,
                case,
                DunningState.DISPUTED,
                "Chargeback dispute initiated via Stripe",
                actor="stripe_webhook",
            )

    # Handle Subscription Cancellation / Churn
    elif event_type == "customer.subscription.deleted":
        cust_id = str(data_obj.get("customer") or "")
        case = (
            db.query(RecoveryCase)
            .filter(RecoveryCase.customer_id == cust_id)
            .filter(RecoveryCase.recovery_status.in_(["pending", "awaiting_payment"]))
            .first()
        )
        if case:
            transition_dunning_state(
                db,
                case,
                DunningState.CHURNED,
                "Subscription cancelled via Stripe",
                actor="stripe_webhook",
            )

    db.commit()
    return WebhookResponse(
        accepted=True, event_id=event_id, message="Stripe webhook processed successfully."
    )


# =========================================================================
# Paddle Webhook Endpoint
# =========================================================================


@router.post("/webhooks/paddle", response_model=WebhookResponse)
async def ingest_paddle_webhook(
    request: Request,
    db: Session = Depends(get_db),
    paddle_signature: Optional[str] = Header(default=None),
):
    raw = await request.body()
    if len(raw) > settings.WEBHOOK_MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Payload exceeds maximum allowed size")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Webhook payload must be valid JSON") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Webhook body must be a JSON object")

    if settings.PADDLE_WEBHOOK_SECRET:
        if not _verify_paddle_signature(raw, paddle_signature or payload.get("p_signature")):
            raise HTTPException(status_code=401, detail="Invalid Paddle webhook signature")
    elif not settings.PADDLE_SIMULATE:
        raise HTTPException(status_code=503, detail="Paddle verification is not configured")

    event_id = str(payload.get("event_id") or payload.get("alert_id") or payload.get("id") or "")
    if not event_id:
        raise HTTPException(status_code=400, detail="Missing Paddle event identifier")

    event_type = str(payload.get("event_type") or payload.get("alert_name") or "")
    if db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first():
        return WebhookResponse(
            accepted=True, event_id=event_id, message="Paddle webhook duplicate ignored."
        )

    db.add(WebhookEvent(event_id=event_id))
    log_event(
        db,
        None,
        "paddle_webhook_received",
        actor="paddle_webhook",
        action=event_type,
        reason=event_id,
    )

    data_obj = payload.get("data") or payload

    if event_type in PADDLE_CONFIRMATION_EVENTS:
        transaction_id = str(data_obj.get("transaction_id") or data_obj.get("order_id") or "")
        case = (
            db.query(RecoveryCase)
            .filter(RecoveryCase.payment_id == transaction_id)
            .filter(RecoveryCase.recovery_status.in_(["awaiting_payment", "pending"]))
            .first()
        )
        if case:
            confirm_provider_payment(db, case, actor="paddle_webhook")
            transition_dunning_state(
                db,
                case,
                DunningState.RECOVERED,
                "Paddle confirmed payment recovery",
                actor="paddle_webhook",
            )

    elif event_type in ("subscription_payment_failed", "payment_failed"):
        cust_id = str(
            data_obj.get("customer_id")
            or data_obj.get("user_id")
            or f"p_cust_{uuid.uuid4().hex[:6]}"
        )
        cust_email = str(data_obj.get("email") or "paddle_subscriber@example.com")
        customer = db.query(Customer).filter(Customer.id == cust_id).first()
        if not customer:
            customer = Customer(id=cust_id, name="Paddle Subscriber", email=cust_email)
            db.add(customer)

        amount = float(data_obj.get("amount") or 49.0)
        currency = str(data_obj.get("currency") or "USD").upper()
        payment_id = str(data_obj.get("transaction_id") or f"pad_tx_{uuid.uuid4().hex[:8]}")
        failure_reason = str(data_obj.get("error_code") or "Payment processing failed via Paddle")

        payment = Payment(
            id=payment_id,
            customer_id=customer.id,
            amount=amount,
            currency=currency,
            status="failed",
            gateway="paddle",
            failure_code="paddle_failed",
            failure_reason=failure_reason,
            timestamp=utcnow(),
        )
        db.add(payment)

        case = RecoveryCase(
            id=f"RC-{uuid.uuid4().hex[:6].upper()}",
            payment_id=payment.id,
            customer_id=customer.id,
            customer_name=customer.name,
            amount_at_risk=amount,
            risk_level="medium",
            failure_category="soft_decline",
            recommended_action="smart_retry",
            reason=failure_reason,
            gateway="paddle",
            evidence={"gateway": "paddle", "event_id": event_id},
            policy_checks={"allowed": True},
        )
        db.add(case)
        db.flush()

        score_case(db, case)
        evaluate_initial_dunning_flow(db, case, payment)
        send_dunning_notification(db, case, NotificationTemplate.GRACE_PERIOD, sequence_step=1)

    db.commit()
    return WebhookResponse(
        accepted=True, event_id=event_id, message="Paddle webhook processed successfully."
    )


# =========================================================================
# Braintree Webhook Endpoint
# =========================================================================


@router.post("/webhooks/braintree", response_model=WebhookResponse)
async def ingest_braintree_webhook(
    request: Request,
    db: Session = Depends(get_db),
    bt_signature: Optional[str] = Header(default=None),
):
    raw = await request.body()
    if len(raw) > settings.WEBHOOK_MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Payload exceeds maximum allowed size")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        # Braintree webhook might post form data or JSON
        payload = {"event": "subscription_charged_unsuccessfully", "id": str(uuid.uuid4())}

    if settings.BRAINTREE_WEBHOOK_SECRET:
        if not _verify_braintree_signature(bt_signature, json.dumps(payload)):
            raise HTTPException(status_code=401, detail="Invalid Braintree webhook signature")
    elif not settings.BRAINTREE_SIMULATE:
        raise HTTPException(status_code=503, detail="Braintree verification is not configured")

    event_id = str(payload.get("id") or payload.get("event_id") or f"bt_evt_{uuid.uuid4().hex[:8]}")
    event_kind = str(
        payload.get("kind") or payload.get("event") or "subscription_charged_unsuccessfully"
    )

    if db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first():
        return WebhookResponse(
            accepted=True, event_id=event_id, message="Braintree duplicate ignored."
        )

    db.add(WebhookEvent(event_id=event_id))
    log_event(
        db,
        None,
        "braintree_webhook_received",
        actor="braintree_webhook",
        action=event_kind,
        reason=event_id,
    )

    if event_kind in BRAINTREE_CONFIRMATION_EVENTS:
        tx_id = str(payload.get("transaction_id") or "")
        case = (
            db.query(RecoveryCase)
            .filter(RecoveryCase.payment_id == tx_id)
            .filter(RecoveryCase.recovery_status.in_(["awaiting_payment", "pending"]))
            .first()
        )
        if case:
            confirm_provider_payment(db, case, actor="braintree_webhook")
            transition_dunning_state(
                db,
                case,
                DunningState.RECOVERED,
                "Braintree confirmed payment recovery",
                actor="braintree_webhook",
            )

    elif "unsuccessful" in event_kind or "declined" in event_kind or "past_due" in event_kind:
        cust_id = str(payload.get("customer_id") or f"bt_cust_{uuid.uuid4().hex[:6]}")
        customer = db.query(Customer).filter(Customer.id == cust_id).first()
        if not customer:
            customer = Customer(
                id=cust_id, name="Braintree Subscriber", email="braintree_subscriber@example.com"
            )
            db.add(customer)

        amount = float(payload.get("amount") or 85.0)
        currency = str(payload.get("currency") or "USD").upper()
        payment_id = str(payload.get("transaction_id") or f"bt_tx_{uuid.uuid4().hex[:8]}")
        failure_reason = str(payload.get("message") or "Braintree payment transaction declined")

        payment = Payment(
            id=payment_id,
            customer_id=customer.id,
            amount=amount,
            currency=currency,
            status="failed",
            gateway="braintree",
            failure_code="braintree_declined",
            failure_reason=failure_reason,
            timestamp=utcnow(),
        )
        db.add(payment)

        case = RecoveryCase(
            id=f"RC-{uuid.uuid4().hex[:6].upper()}",
            payment_id=payment.id,
            customer_id=customer.id,
            customer_name=customer.name,
            amount_at_risk=amount,
            risk_level="medium",
            failure_category="soft_decline",
            recommended_action="smart_retry",
            reason=failure_reason,
            gateway="braintree",
            evidence={"gateway": "braintree", "event_id": event_id},
            policy_checks={"allowed": True},
        )
        db.add(case)
        db.flush()

        score_case(db, case)
        evaluate_initial_dunning_flow(db, case, payment)
        send_dunning_notification(db, case, NotificationTemplate.GRACE_PERIOD, sequence_step=1)

    db.commit()
    return WebhookResponse(
        accepted=True, event_id=event_id, message="Braintree webhook processed successfully."
    )
