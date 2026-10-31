"""AI Churn Risk & Recovery Scoring Model.

Evaluates subscriber tenure, failure reason category, historical recovery rates,
and amount at risk to produce a calibrated 0-100 recovery probability score,
churn risk level, and explainable intervention strategy.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from ..models import Customer, Payment, RecoveryCase
from ..utils.time import utcnow
from .dunning_engine import DeclineCategory, classify_decline

logger = logging.getLogger("recoverai.scoring")


class RiskTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendedStrategy(str, Enum):
    SMART_RETRY_IMMEDIATE = "smart_retry_immediate"
    PAYDAY_ALIGNED_RETRY = "payday_aligned_retry"
    FRIENDLY_DUNNING_SEQUENCE = "friendly_dunning_sequence"
    URGENT_CARD_UPDATE = "urgent_card_update"
    HIGH_TOUCH_VOICE_AGENT = "high_touch_voice_agent"
    MANUAL_INTERVENTION_HOLD = "manual_intervention_hold"


@dataclass(frozen=True)
class ChurnScoreResult:
    recovery_probability: float  # 0.0 to 100.0
    churn_risk_score: float  # 0.0 to 100.0
    risk_tier: RiskTier
    expected_recovery_mrr: float
    recommended_strategy: RecommendedStrategy
    key_factors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recovery_probability": round(self.recovery_probability, 1),
            "churn_risk_score": round(self.churn_risk_score, 1),
            "risk_tier": self.risk_tier.value,
            "expected_recovery_mrr": round(self.expected_recovery_mrr, 2),
            "recommended_strategy": self.recommended_strategy.value,
            "key_factors": self.key_factors,
        }


def _calculate_tenure_weight(tenure_months: int) -> Tuple[float, Optional[str]]:
    """Tenure factor: longer-tenured subscribers churn significantly less."""
    if tenure_months >= 24:
        return (
            20.0,
            f"Loyal subscriber tenure ({tenure_months} months) boosts recovery likelihood (+20%)",
        )
    if tenure_months >= 12:
        return (
            15.0,
            f"Mature subscriber tenure ({tenure_months} months) indicates low voluntary churn (+15%)",
        )
    if tenure_months >= 6:
        return 10.0, f"Established subscriber tenure ({tenure_months} months) (+10%)"
    if tenure_months >= 3:
        return 5.0, "Moderate subscriber tenure (3-5 months)"
    return -10.0, "New subscriber (< 3 months); high early-tenure abandonment risk (-10%)"


def _calculate_failure_impact(category: DeclineCategory) -> Tuple[float, str]:
    """Base recovery rate impact by failure category."""
    if category == DeclineCategory.NETWORK_TIMEOUT:
        return 45.0, "Transient network / system failure has highest natural recovery rate (85-95%)"
    if category == DeclineCategory.INSUFFICIENT_FUNDS:
        return (
            30.0,
            "Insufficient funds requires liquidity alignment but has moderate recovery (65-75%)",
        )
    if category == DeclineCategory.DO_NOT_HONOR:
        return 20.0, "Generic bank decline requires issuer check or re-authentication (45-55%)"
    if category == DeclineCategory.EXPIRED_CARD:
        return 15.0, "Expired card requires customer update action; moderate friction (40-50%)"
    if category == DeclineCategory.HARD_DECLINE:
        return -40.0, "Stolen/lost/terminal decline cannot be recovered automatically (< 5%)"
    return 25.0, "Soft decline with standard recovery prospects"


def _calculate_history_weight(
    total_payments: int,
    success_rate: float,
    previous_failures: int,
) -> Tuple[float, Optional[str]]:
    """Historical behavior score from previous payment records."""
    if total_payments == 0:
        return 0.0, "First transaction on account; no historical payment baseline"

    score_delta = 0.0
    notes = []

    if success_rate >= 90.0:
        score_delta += 15.0
        notes.append(f"Strong historical payment success rate ({success_rate:.0f}%) (+15%)")
    elif success_rate >= 70.0:
        score_delta += 8.0
        notes.append(f"Good payment history ({success_rate:.0f}%) (+8%)")
    elif success_rate < 50.0:
        score_delta -= 15.0
        notes.append(f"Poor payment history ({success_rate:.0f}%) elevates churn risk (-15%)")

    if previous_failures >= 3:
        score_delta -= 10.0
        notes.append(
            f"Multiple recent failures ({previous_failures}) indicate persistent payment issue (-10%)"
        )

    return score_delta, "; ".join(notes) if notes else None


def _calculate_amount_friction(amount: float) -> Tuple[float, Optional[str]]:
    """Transaction amount friction."""
    if amount > 10000.0:
        return (
            -10.0,
            f"High value amount ({amount:.2f}) carries higher friction for auto-retry (-10%)",
        )
    if amount < 100.0:
        return 5.0, f"Micro-transaction amount ({amount:.2f}) has minimal liquidity friction (+5%)"
    return 0.0, None


def _select_strategy(
    category: DeclineCategory,
    recovery_prob: float,
    amount: float,
) -> RecommendedStrategy:
    """Recommend optimal revenue recovery strategy based on category and probability."""
    if category == DeclineCategory.HARD_DECLINE:
        return RecommendedStrategy.MANUAL_INTERVENTION_HOLD
    if category == DeclineCategory.EXPIRED_CARD:
        return RecommendedStrategy.URGENT_CARD_UPDATE
    if category == DeclineCategory.NETWORK_TIMEOUT:
        return RecommendedStrategy.SMART_RETRY_IMMEDIATE
    if category == DeclineCategory.INSUFFICIENT_FUNDS:
        return RecommendedStrategy.PAYDAY_ALIGNED_RETRY
    if amount >= 5000.0 or recovery_prob < 40.0:
        return RecommendedStrategy.HIGH_TOUCH_VOICE_AGENT
    return RecommendedStrategy.FRIENDLY_DUNNING_SEQUENCE


def score_recovery_probability(
    tenure_months: int,
    decline_code: Optional[str],
    failure_reason: Optional[str],
    amount: float,
    total_payments: int = 0,
    success_rate: float = 100.0,
    previous_failures: int = 0,
    attempt_number: int = 1,
) -> ChurnScoreResult:
    """Evaluate recovery probability and churn risk across features."""
    category = classify_decline(decline_code, failure_reason)
    factors: List[str] = []

    # Baseline probability
    base_prob = 40.0

    # 1. Failure Category Impact
    cat_delta, cat_note = _calculate_failure_impact(category)
    base_prob += cat_delta
    factors.append(cat_note)

    # 2. Tenure Impact
    tenure_delta, tenure_note = _calculate_tenure_weight(tenure_months)
    base_prob += tenure_delta
    if tenure_note:
        factors.append(tenure_note)

    # 3. History Impact
    hist_delta, hist_note = _calculate_history_weight(
        total_payments, success_rate, previous_failures
    )
    base_prob += hist_delta
    if hist_note:
        factors.append(hist_note)

    # 4. Amount Friction
    amt_delta, amt_note = _calculate_amount_friction(amount)
    base_prob += amt_delta
    if amt_note:
        factors.append(amt_note)

    # 5. Retry Attempt Degradation
    if attempt_number > 1:
        attempt_penalty = (attempt_number - 1) * 12.0
        base_prob -= attempt_penalty
        factors.append(
            f"Subsequent attempt #{attempt_number} reduces marginal probability (-{attempt_penalty:.0f}%)"
        )

    # Clamp probability to [0.0, 100.0]
    final_prob = max(0.0, min(100.0, base_prob))
    churn_risk = 100.0 - final_prob

    # Risk Tier assignment
    if final_prob >= 75.0:
        tier = RiskTier.LOW
    elif final_prob >= 50.0:
        tier = RiskTier.MEDIUM
    elif final_prob >= 25.0:
        tier = RiskTier.HIGH
    else:
        tier = RiskTier.CRITICAL

    strategy = _select_strategy(category, final_prob, amount)
    expected_mrr = amount * (final_prob / 100.0)

    return ChurnScoreResult(
        recovery_probability=final_prob,
        churn_risk_score=churn_risk,
        risk_tier=tier,
        expected_recovery_mrr=expected_mrr,
        recommended_strategy=strategy,
        key_factors=factors,
    )


def score_case(db: Session, case: RecoveryCase) -> ChurnScoreResult:
    """Evaluate and store churn risk score for an active recovery case."""
    customer = db.query(Customer).filter(Customer.id == case.customer_id).first()
    payment = db.query(Payment).filter(Payment.id == case.payment_id).first()

    total_payments = 0
    successful_payments = 0
    previous_failures = 0
    tenure_months = 6  # default if first payment

    if customer:
        payments = db.query(Payment).filter(Payment.customer_id == customer.id).all()
        total_payments = len(payments)
        successful_payments = sum(1 for p in payments if p.status == "success")
        previous_failures = sum(1 for p in payments if p.status == "failed")
        if payments:
            earliest = min((p.timestamp for p in payments if p.timestamp), default=None)
            if earliest:
                now_dt = utcnow().replace(tzinfo=None)
                earliest_dt = (
                    earliest.replace(tzinfo=None) if hasattr(earliest, "replace") else earliest
                )
                days_diff = max(0, (now_dt - earliest_dt).days)
                tenure_months = max(1, days_diff // 30)

    success_rate = (successful_payments / total_payments * 100.0) if total_payments > 0 else 0.0

    result = score_recovery_probability(
        tenure_months=tenure_months,
        decline_code=payment.failure_code if payment else None,
        failure_reason=payment.failure_reason if payment else case.reason,
        amount=case.amount_at_risk,
        total_payments=total_payments,
        success_rate=success_rate,
        previous_failures=previous_failures,
        attempt_number=(case.retry_count or 0) + 1,
    )

    case.recovery_probability = result.recovery_probability
    case.churn_risk_score = result.churn_risk_score
    case.risk_level = result.risk_tier.value

    return result
