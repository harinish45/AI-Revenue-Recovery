"""Dunning Engine & Smart Payment Retry State Machine.

Dynamic retry scheduling with exponential backoff and card network heuristics
(Visa, Mastercard, Amex, Discover, RuPay). Guides recovery cases through
policy-safe lifecycle states from initial failure to recovery or churn.
"""

import hashlib
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from ..config import settings
from ..models import Payment, RecoveryCase
from ..services.audit_service import log_event
from ..utils.time import utcnow

logger = logging.getLogger("recoverai.dunning")


class DunningState(str, Enum):
    INITIAL_FAILURE = "initial_failure"
    GRACE_PERIOD = "grace_period"
    SOFT_RETRY_SCHEDULED = "soft_retry_scheduled"
    CARD_UPDATE_REQUESTED = "card_update_requested"
    CARD_UPDATED = "card_updated"
    RETRY_EXECUTED = "retry_executed"
    AWAITING_PAYMENT = "awaiting_payment"
    RECOVERED = "recovered"
    HARD_DECLINED = "hard_declined"
    DISPUTED = "disputed"
    CHURNED = "churned"
    ESCALATED = "escalated"
    SKIPPED = "skipped"


class DeclineCategory(str, Enum):
    SOFT_DECLINE = "soft_decline"
    HARD_DECLINE = "hard_decline"
    EXPIRED_CARD = "expired_card"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    NETWORK_TIMEOUT = "network_timeout"
    DO_NOT_HONOR = "do_not_honor"
    FRAUD_OR_RESTRICTED = "fraud_or_restricted"


# ISO 8583 / Gateway network response code mappings
HARD_DECLINE_CODES = {
    "04",
    "07",
    "14",
    "15",
    "41",
    "43",
    "57",
    "58",
    "stolen_card",
    "lost_card",
    "pickup_card",
    "fraudulent",
    "account_closed",
    "invalid_account_number",
}

EXPIRED_CODES = {
    "54",
    "expired_card",
    "invalid_expiry_date",
    "expired_token",
}

INSUFFICIENT_FUNDS_CODES = {
    "51",
    "insufficient_funds",
    "insufficient_balance",
}

NETWORK_TIMEOUT_CODES = {
    "06",
    "19",
    "91",
    "96",
    "TO",
    "network_timeout",
    "processing_error",
    "issuer_not_available",
    "system_malfunction",
    "gateway_error",
}

DO_NOT_HONOR_CODES = {
    "05",
    "do_not_honor",
    "generic_decline",
}


def classify_decline(code: Optional[str], reason: Optional[str]) -> DeclineCategory:
    """Classify gateway decline code and reason into actionable category."""
    normalized_code = (code or "").strip().lower()
    normalized_reason = (reason or "").strip().lower()

    if normalized_code in HARD_DECLINE_CODES or any(
        w in normalized_reason for w in ["stolen", "lost", "fraud", "closed"]
    ):
        return DeclineCategory.HARD_DECLINE
    if normalized_code in EXPIRED_CODES or "expired" in normalized_reason:
        return DeclineCategory.EXPIRED_CARD
    if normalized_code in INSUFFICIENT_FUNDS_CODES or "insufficient" in normalized_reason:
        return DeclineCategory.INSUFFICIENT_FUNDS
    if normalized_code in NETWORK_TIMEOUT_CODES or any(
        w in normalized_reason for w in ["timeout", "system", "gateway", "unavailable"]
    ):
        return DeclineCategory.NETWORK_TIMEOUT
    if normalized_code in DO_NOT_HONOR_CODES or "do not honor" in normalized_reason:
        return DeclineCategory.DO_NOT_HONOR
    return DeclineCategory.SOFT_DECLINE


def is_retryable(category: DeclineCategory) -> bool:
    """Determine if a decline category can be retried automatically."""
    return category not in (DeclineCategory.HARD_DECLINE, DeclineCategory.EXPIRED_CARD)


def _compute_deterministic_jitter(
    seed_key: str, min_fraction: float = -0.15, max_fraction: float = 0.15
) -> float:
    """Generate deterministic pseudo-random jitter factor from a seed key."""
    digest = hashlib.sha256(seed_key.encode("utf-8")).hexdigest()
    ratio = int(digest[:8], 16) / 0xFFFFFFFF
    return min_fraction + ratio * (max_fraction - min_fraction)


def calculate_retry_delay_hours(
    attempt: int,
    category: DeclineCategory,
    card_brand: Optional[str] = None,
    seed_key: Optional[str] = None,
) -> float:
    """Compute exponential backoff delay in hours with network-specific heuristics."""
    attempt_clamped = max(1, attempt)
    base_hours = settings.RETRY_COOLDOWN_FIRST_HOURS

    if category == DeclineCategory.NETWORK_TIMEOUT:
        # Fast retry: transient network glitches resolve quickly
        base_delay = 4.0 * (1.8 ** (attempt_clamped - 1))
    elif category == DeclineCategory.INSUFFICIENT_FUNDS:
        # Liquidity issue: longer backoff to allow account replenishment
        brand = (card_brand or "").lower()
        if brand in ("visa", "mastercard"):
            base_delay = 48.0 if attempt_clamped == 1 else 72.0
        else:
            base_delay = 36.0 if attempt_clamped == 1 else 60.0
    elif category == DeclineCategory.DO_NOT_HONOR:
        base_delay = 24.0 * attempt_clamped
    else:
        # Standard soft decline exponential backoff
        base_delay = base_hours * (2.0 ** (attempt_clamped - 1))

    # Apply bounded deterministic jitter to prevent thundering herds
    jitter_factor = _compute_deterministic_jitter(seed_key or f"retry-{attempt}-{category}")
    delay = base_delay * (1.0 + jitter_factor)
    return round(max(1.0, delay), 2)


def align_to_optimal_business_hours(target: datetime) -> datetime:
    """Align scheduled retry to optimal payment success window (09:00 - 18:00 UTC)."""
    if target.hour < 9:
        return target.replace(hour=9, minute=0, second=0, microsecond=0)
    if target.hour >= 18:
        next_day = target + timedelta(days=1)
        return next_day.replace(hour=9, minute=0, second=0, microsecond=0)
    return target


def schedule_next_retry(
    attempt: int,
    category: DeclineCategory,
    card_brand: Optional[str] = None,
    base_time: Optional[datetime] = None,
    seed_key: Optional[str] = None,
) -> datetime:
    """Calculate the next optimal retry timestamp applying backoff and heuristics."""
    start_time = base_time or utcnow()
    delay_hours = calculate_retry_delay_hours(attempt, category, card_brand, seed_key)
    target_time = start_time + timedelta(hours=delay_hours)
    return align_to_optimal_business_hours(target_time)


# Allowed state transition graph
VALID_TRANSITIONS: Dict[str, List[str]] = {
    "pending": [
        DunningState.GRACE_PERIOD.value,
        DunningState.SOFT_RETRY_SCHEDULED.value,
        DunningState.CARD_UPDATE_REQUESTED.value,
        DunningState.HARD_DECLINED.value,
        DunningState.ESCALATED.value,
        DunningState.SKIPPED.value,
    ],
    DunningState.INITIAL_FAILURE.value: [
        DunningState.GRACE_PERIOD.value,
        DunningState.SOFT_RETRY_SCHEDULED.value,
        DunningState.CARD_UPDATE_REQUESTED.value,
        DunningState.HARD_DECLINED.value,
        DunningState.ESCALATED.value,
        DunningState.SKIPPED.value,
    ],
    DunningState.GRACE_PERIOD.value: [
        DunningState.SOFT_RETRY_SCHEDULED.value,
        DunningState.CARD_UPDATE_REQUESTED.value,
        DunningState.RETRY_EXECUTED.value,
        DunningState.RECOVERED.value,
        DunningState.CHURNED.value,
        DunningState.ESCALATED.value,
    ],
    DunningState.SOFT_RETRY_SCHEDULED.value: [
        DunningState.RETRY_EXECUTED.value,
        DunningState.AWAITING_PAYMENT.value,
        DunningState.CARD_UPDATE_REQUESTED.value,
        DunningState.ESCALATED.value,
        DunningState.CHURNED.value,
        DunningState.RECOVERED.value,
    ],
    DunningState.CARD_UPDATE_REQUESTED.value: [
        DunningState.CARD_UPDATED.value,
        DunningState.CHURNED.value,
        DunningState.ESCALATED.value,
        DunningState.RECOVERED.value,
    ],
    DunningState.CARD_UPDATED.value: [
        DunningState.SOFT_RETRY_SCHEDULED.value,
        DunningState.RETRY_EXECUTED.value,
        DunningState.RECOVERED.value,
    ],
    DunningState.RETRY_EXECUTED.value: [
        DunningState.RECOVERED.value,
        DunningState.SOFT_RETRY_SCHEDULED.value,
        DunningState.CARD_UPDATE_REQUESTED.value,
        DunningState.CHURNED.value,
        DunningState.ESCALATED.value,
    ],
    DunningState.AWAITING_PAYMENT.value: [
        DunningState.RECOVERED.value,
        DunningState.CHURNED.value,
        DunningState.ESCALATED.value,
    ],
    DunningState.DISPUTED.value: [
        DunningState.ESCALATED.value,
        DunningState.CHURNED.value,
        DunningState.RECOVERED.value,
    ],
    DunningState.HARD_DECLINED.value: [],
    DunningState.RECOVERED.value: [],
    DunningState.CHURNED.value: [],
    DunningState.SKIPPED.value: [],
    DunningState.ESCALATED.value: [
        DunningState.RECOVERED.value,
        DunningState.CHURNED.value,
    ],
}


def can_transition(current_state: str, next_state: DunningState) -> bool:
    """Validate if transitioning from current_state to next_state is permitted."""
    allowed = VALID_TRANSITIONS.get(current_state, [])
    return next_state.value in allowed


def transition_dunning_state(
    db: Session,
    case: RecoveryCase,
    target_state: DunningState,
    reason: str,
    actor: str = "dunning_engine",
    metadata: Optional[Dict[str, Any]] = None,
) -> RecoveryCase:
    """Safely advance case through dunning state machine with audit logging."""
    current_state = case.dunning_state or "pending"
    if current_state == target_state.value:
        return case

    if not can_transition(current_state, target_state):
        logger.warning(
            f"Invalid dunning transition attempted for case {case.id}: "
            f"{current_state} -> {target_state.value}"
        )
        target_state = DunningState.ESCALATED
        reason = f"Invalid transition from {current_state} attempted; safely escalated."

    case.dunning_state = target_state.value
    case.updated_at = utcnow()

    # Sync recovery_status when terminal or waiting
    if target_state == DunningState.RECOVERED:
        case.recovery_status = "recovered"
    elif target_state == DunningState.HARD_DECLINED:
        case.recovery_status = "failed"
    elif target_state == DunningState.CHURNED:
        case.recovery_status = "failed"
    elif target_state == DunningState.ESCALATED:
        case.recovery_status = "needs_human_review"
    elif target_state == DunningState.AWAITING_PAYMENT:
        case.recovery_status = "awaiting_payment"

    log_event(
        db=db,
        case_id=case.id,
        event_type="dunning_state_transition",
        actor=actor,
        decision=target_state.value,
        reason=reason,
        action=f"transition_to_{target_state.value}",
        result=target_state.value,
    )
    return case


def evaluate_initial_dunning_flow(
    db: Session,
    case: RecoveryCase,
    payment: Payment,
) -> Tuple[DunningState, Optional[datetime], str]:
    """Determine initial dunning state and next retry schedule upon payment failure."""
    category = classify_decline(payment.failure_code, payment.failure_reason)

    if category == DeclineCategory.HARD_DECLINE:
        transition_dunning_state(
            db,
            case,
            DunningState.HARD_DECLINED,
            "Terminal decline (stolen/fraud/lost card); no retry permitted.",
            actor="dunning_engine",
        )
        return DunningState.HARD_DECLINED, None, "Hard decline; subscription halted"

    if category == DeclineCategory.EXPIRED_CARD:
        transition_dunning_state(
            db,
            case,
            DunningState.CARD_UPDATE_REQUESTED,
            "Card expired; customer notification sequence triggered for payment method update.",
            actor="dunning_engine",
        )
        return DunningState.CARD_UPDATE_REQUESTED, None, "Payment method expired; update requested"

    # Soft decline / liquidity / network: enter Grace Period with smart retry schedule
    transition_dunning_state(
        db,
        case,
        DunningState.GRACE_PERIOD,
        f"Soft failure categorized as {category.value}; entered grace period.",
        actor="dunning_engine",
    )

    next_retry = schedule_next_retry(
        attempt=1,
        category=category,
        card_brand=payment.card_brand,
        base_time=payment.timestamp or utcnow(),
        seed_key=case.id,
    )
    case.next_retry_at = next_retry
    case.failure_category = category.value

    transition_dunning_state(
        db,
        case,
        DunningState.SOFT_RETRY_SCHEDULED,
        f"Smart retry scheduled for {next_retry.isoformat()} based on {category.value} heuristics.",
        actor="dunning_engine",
    )

    return (
        DunningState.SOFT_RETRY_SCHEDULED,
        next_retry,
        f"Smart retry scheduled for {next_retry.isoformat()}",
    )
