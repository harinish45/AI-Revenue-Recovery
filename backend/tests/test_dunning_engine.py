from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Payment, RecoveryCase
from app.services.dunning_engine import (
    DeclineCategory,
    DunningState,
    align_to_optimal_business_hours,
    calculate_retry_delay_hours,
    can_transition,
    classify_decline,
    evaluate_initial_dunning_flow,
    is_retryable,
    transition_dunning_state,
)


def test_classify_decline_codes():
    assert classify_decline("41", "lost card") == DeclineCategory.HARD_DECLINE
    assert classify_decline("stolen_card", "") == DeclineCategory.HARD_DECLINE
    assert classify_decline("54", "card expired") == DeclineCategory.EXPIRED_CARD
    assert classify_decline("expired_card", "expired") == DeclineCategory.EXPIRED_CARD
    assert classify_decline("51", "insufficient funds") == DeclineCategory.INSUFFICIENT_FUNDS
    assert classify_decline("91", "system malfunction") == DeclineCategory.NETWORK_TIMEOUT
    assert classify_decline("05", "do not honor") == DeclineCategory.DO_NOT_HONOR
    assert classify_decline("unknown_code", "unknown error") == DeclineCategory.SOFT_DECLINE


def test_is_retryable():
    assert is_retryable(DeclineCategory.SOFT_DECLINE) is True
    assert is_retryable(DeclineCategory.INSUFFICIENT_FUNDS) is True
    assert is_retryable(DeclineCategory.NETWORK_TIMEOUT) is True
    assert is_retryable(DeclineCategory.HARD_DECLINE) is False
    assert is_retryable(DeclineCategory.EXPIRED_CARD) is False


def test_retry_delay_heuristics():
    # Network timeout has shorter delay
    delay_timeout = calculate_retry_delay_hours(1, DeclineCategory.NETWORK_TIMEOUT)
    assert 3.0 <= delay_timeout <= 6.0

    # Insufficient funds on Visa/Mastercard gives 48h or 72h window
    delay_liquidity_v1 = calculate_retry_delay_hours(
        1, DeclineCategory.INSUFFICIENT_FUNDS, card_brand="visa"
    )
    assert 40.0 <= delay_liquidity_v1 <= 60.0

    delay_liquidity_v2 = calculate_retry_delay_hours(
        2, DeclineCategory.INSUFFICIENT_FUNDS, card_brand="mastercard"
    )
    assert 60.0 <= delay_liquidity_v2 <= 85.0

    # Backoff increases with attempts
    delay_att1 = calculate_retry_delay_hours(1, DeclineCategory.SOFT_DECLINE)
    delay_att2 = calculate_retry_delay_hours(2, DeclineCategory.SOFT_DECLINE)
    assert delay_att2 > delay_att1


def test_align_to_optimal_business_hours():
    # 03:00 UTC should align to 09:00 UTC same day
    dt_early = datetime(2026, 11, 15, 3, 30, tzinfo=timezone.utc)
    aligned_early = align_to_optimal_business_hours(dt_early)
    assert aligned_early.hour == 9
    assert aligned_early.day == 15

    # 19:00 UTC should roll over to 09:00 UTC next day
    dt_late = datetime(2026, 11, 15, 19, 0, tzinfo=timezone.utc)
    aligned_late = align_to_optimal_business_hours(dt_late)
    assert aligned_late.hour == 9
    assert aligned_late.day == 16


def test_dunning_valid_and_invalid_transitions(db_session: Session):
    case = RecoveryCase(
        id="RC-TEST-DUNNING-1",
        amount_at_risk=1500.0,
        risk_level="medium",
        failure_category="insufficient_funds",
        recommended_action="smart_retry",
        reason="Insufficient funds",
        dunning_state=DunningState.GRACE_PERIOD.value,
        recovery_status="pending",
    )
    db_session.add(case)
    db_session.commit()

    # Valid transition: grace_period -> soft_retry_scheduled
    assert can_transition(case.dunning_state, DunningState.SOFT_RETRY_SCHEDULED) is True
    transition_dunning_state(
        db_session, case, DunningState.SOFT_RETRY_SCHEDULED, "Scheduled soft retry"
    )
    assert case.dunning_state == DunningState.SOFT_RETRY_SCHEDULED.value

    # Valid transition: soft_retry_scheduled -> recovered
    assert can_transition(case.dunning_state, DunningState.RECOVERED) is True
    transition_dunning_state(db_session, case, DunningState.RECOVERED, "Payment recovered")
    assert case.dunning_state == DunningState.RECOVERED.value

    # Invalid transition: terminal state recovered cannot transition to initial_failure
    assert can_transition(case.dunning_state, DunningState.INITIAL_FAILURE) is False


def test_evaluate_initial_dunning_flow(db_session: Session):
    payment_hard = Payment(
        id="pay_hard_001",
        amount=2000.0,
        status="failed",
        failure_code="41",
        failure_reason="stolen card reported",
    )
    case_hard = RecoveryCase(
        id="RC-HARD-001",
        payment_id=payment_hard.id,
        amount_at_risk=payment_hard.amount,
        recovery_status="pending",
        dunning_state="pending",
    )
    db_session.add_all([payment_hard, case_hard])
    db_session.commit()

    state, retry_at, _ = evaluate_initial_dunning_flow(db_session, case_hard, payment_hard)
    assert state == DunningState.HARD_DECLINED
    assert retry_at is None
    assert case_hard.recovery_status == "failed"

    # Test expired card
    payment_exp = Payment(
        id="pay_exp_001",
        amount=1200.0,
        status="failed",
        failure_code="54",
        failure_reason="expired card",
    )
    case_exp = RecoveryCase(
        id="RC-EXP-001",
        payment_id=payment_exp.id,
        amount_at_risk=payment_exp.amount,
        recovery_status="pending",
        dunning_state="pending",
    )
    db_session.add_all([payment_exp, case_exp])
    db_session.commit()

    state, retry_at, _ = evaluate_initial_dunning_flow(db_session, case_exp, payment_exp)
    assert state == DunningState.CARD_UPDATE_REQUESTED
    assert retry_at is None
