from app.services.churn_scoring import (
    RecommendedStrategy,
    RiskTier,
    score_recovery_probability,
)


def test_tenure_impacts_score():
    score_loyal = score_recovery_probability(
        tenure_months=24,
        decline_code="insufficient_funds",
        failure_reason="Insufficient balance",
        amount=1000.0,
    )
    score_new = score_recovery_probability(
        tenure_months=1,
        decline_code="insufficient_funds",
        failure_reason="Insufficient balance",
        amount=1000.0,
    )
    assert score_loyal.recovery_probability > score_new.recovery_probability
    assert score_loyal.churn_risk_score < score_new.churn_risk_score
    assert any("tenure" in factor.lower() for factor in score_loyal.key_factors)


def test_failure_category_impacts_strategy():
    score_network = score_recovery_probability(
        tenure_months=12,
        decline_code="91",
        failure_reason="network timeout",
        amount=500.0,
    )
    assert score_network.recovery_probability >= 70.0
    assert score_network.recommended_strategy == RecommendedStrategy.SMART_RETRY_IMMEDIATE

    score_expired = score_recovery_probability(
        tenure_months=12,
        decline_code="54",
        failure_reason="expired card",
        amount=500.0,
    )
    assert score_expired.recommended_strategy == RecommendedStrategy.URGENT_CARD_UPDATE

    score_hard = score_recovery_probability(
        tenure_months=12,
        decline_code="41",
        failure_reason="stolen card",
        amount=500.0,
    )
    assert score_hard.risk_tier == RiskTier.CRITICAL
    assert score_hard.recommended_strategy == RecommendedStrategy.MANUAL_INTERVENTION_HOLD


def test_attempt_degradation():
    score_att1 = score_recovery_probability(
        tenure_months=6,
        decline_code="51",
        failure_reason="insufficient funds",
        amount=1500.0,
        attempt_number=1,
    )
    score_att3 = score_recovery_probability(
        tenure_months=6,
        decline_code="51",
        failure_reason="insufficient funds",
        amount=1500.0,
        attempt_number=3,
    )
    assert score_att1.recovery_probability > score_att3.recovery_probability


def test_expected_mrr_calculation():
    amount = 5000.0
    res = score_recovery_probability(
        tenure_months=12,
        decline_code="51",
        failure_reason="insufficient funds",
        amount=amount,
    )
    expected = amount * (res.recovery_probability / 100.0)
    assert abs(res.expected_recovery_mrr - expected) < 0.01
