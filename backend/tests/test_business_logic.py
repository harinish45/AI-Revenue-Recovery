from app.models import Customer, Payment, RecoveryCase
from app.services import batch_executor
from app.services.batch_executor import run_batch_recovery
from app.services.decision_engine import diagnose_and_recommend
from app.services.metrics_service import get_metrics
from app.services.policy_engine import evaluate_policy


def _make_customer_and_payment(
    db_session, status="failed", failure_reason="Gateway timeout", amount=2000.0
):
    customer = Customer(
        id="cus_qa", name="QA Customer", email="qa@recoverai.demo", phone="+919876543210"
    )
    payment = Payment(
        id="pay_test",
        customer_id=customer.id,
        amount=amount,
        status=status,
        failure_reason=failure_reason,
    )
    db_session.add_all([customer, payment])
    db_session.commit()
    return customer, payment


def test_policy_blocks_amount_above_threshold(db_session):
    _, payment = _make_customer_and_payment(db_session, amount=999999.0)
    case = RecoveryCase(
        id="RC-1",
        payment_id=payment.id,
        customer_id=payment.customer_id,
        customer_name="Test",
        amount_at_risk=payment.amount,
        risk_level="high",
        failure_category="bank_rejection",
        recommended_action="needs_human_review",
        reason="test",
        evidence={},
        retry_count=0,
        max_retries=2,
        recovery_status="pending",
    )
    allowed, checks, reasons = evaluate_policy(db_session, case, payment)
    assert allowed is False
    assert checks["amount_limit_check"] is False
    assert any("Amount exceeds" in r for r in reasons)


def test_policy_blocks_case_already_in_terminal_state(db_session):
    _, payment = _make_customer_and_payment(db_session)
    case = RecoveryCase(
        id="RC-2",
        payment_id=payment.id,
        customer_id=payment.customer_id,
        customer_name="Test",
        amount_at_risk=payment.amount,
        risk_level="low",
        failure_category="temporary_gateway_failure",
        recommended_action="retry_payment",
        reason="test",
        evidence={},
        retry_count=0,
        max_retries=2,
        recovery_status="recovered",
    )
    allowed, checks, reasons = evaluate_policy(db_session, case, payment)
    assert allowed is False
    assert checks["terminal_state_check"] is False


def test_policy_allows_eligible_failed_payment_under_threshold(db_session):
    _, payment = _make_customer_and_payment(db_session, amount=2500.0)
    case = RecoveryCase(
        id="RC-3",
        payment_id=payment.id,
        customer_id=payment.customer_id,
        customer_name="Test",
        amount_at_risk=payment.amount,
        risk_level="low",
        failure_category="temporary_gateway_failure",
        recommended_action="retry_payment",
        reason="test",
        evidence={},
        retry_count=0,
        max_retries=2,
        recovery_status="pending",
    )
    allowed, checks, reasons = evaluate_policy(db_session, case, payment)
    assert allowed is True
    assert reasons == []


def test_decision_engine_flags_gateway_timeout_as_low_risk_retry(db_session):
    customer, payment = _make_customer_and_payment(db_session, failure_reason="Gateway timeout")
    category, action, reason, evidence, risk_level = diagnose_and_recommend(
        db_session, payment, customer
    )
    assert category == "temporary_gateway_failure"
    assert action == "retry_payment"
    assert risk_level == "low"
    assert evidence["total_payments"] == 1


def test_decision_engine_confidence_reflects_real_customer_history(db_session):
    """diagnose_and_recommend queries the customer's actual payment rows for
    evidence -- confidence must move with that history, end to end through
    the real DB-backed path (not just the isolated agent function)."""
    troubled_customer = Customer(id="cus_troubled", name="Troubled", email="t@recoverai.demo")
    clean_customer = Customer(id="cus_clean", name="Clean", email="c@recoverai.demo")
    db_session.add_all([troubled_customer, clean_customer])

    troubled_payment = Payment(
        id="pay_troubled_current",
        customer_id="cus_troubled",
        amount=2000.0,
        status="failed",
        failure_reason="Gateway timeout",
    )
    db_session.add(troubled_payment)
    for i in range(4):
        db_session.add(
            Payment(
                id=f"pay_troubled_prior_{i}",
                customer_id="cus_troubled",
                amount=500.0,
                status="failed",
                failure_reason="Gateway timeout",
            )
        )

    clean_payment = Payment(
        id="pay_clean_current",
        customer_id="cus_clean",
        amount=2000.0,
        status="failed",
        failure_reason="Gateway timeout",
    )
    db_session.add(clean_payment)
    for i in range(6):
        db_session.add(
            Payment(
                id=f"pay_clean_prior_{i}", customer_id="cus_clean", amount=500.0, status="success"
            )
        )
    db_session.commit()

    _, _, _, troubled_evidence, _ = diagnose_and_recommend(
        db_session, troubled_payment, troubled_customer
    )
    _, _, _, clean_evidence, _ = diagnose_and_recommend(db_session, clean_payment, clean_customer)

    assert clean_evidence["confidence"] > troubled_evidence["confidence"]


def test_decision_engine_flags_bank_decline_as_high_risk_review(db_session):
    customer, payment = _make_customer_and_payment(
        db_session, failure_reason="Bank declined transaction"
    )
    category, action, reason, evidence, risk_level = diagnose_and_recommend(
        db_session, payment, customer
    )
    assert category == "bank_rejection"
    assert action == "needs_human_review"
    assert risk_level == "high"


def test_metrics_service_computes_recovery_rate_from_real_rows(db_session):
    customer, payment = _make_customer_and_payment(db_session, status="failed", amount=1000.0)
    case = RecoveryCase(
        id="RC-4",
        payment_id=payment.id,
        customer_id=customer.id,
        customer_name=customer.name,
        amount_at_risk=1000.0,
        risk_level="low",
        failure_category="temporary_gateway_failure",
        recommended_action="retry_payment",
        reason="test",
        evidence={},
        retry_count=1,
        max_retries=2,
        recovery_status="recovered",
        recovered_amount=1000.0,
    )
    db_session.add(case)
    db_session.commit()

    metrics = get_metrics(db_session)
    assert metrics["failed_payments"] == 1
    assert metrics["recovered_amount"] == 1000.0
    assert metrics["successful_recoveries"] == 1
    assert metrics["recovery_rate"] == 100.0


def test_batch_recovery_counts_an_unexpected_exception_as_errored_not_escalated(
    db_session, monkeypatch
):
    """A case whose execution raises must not be silently folded into
    "escalated" -- that implies the policy engine made a decision and the
    case record reflects it. An exception means execute_recovery never got
    that far, and db.rollback() leaves the case exactly as it was, so the
    batch summary must not claim it was routed to human review."""
    _, payment = _make_customer_and_payment(db_session, amount=2000.0)
    case = RecoveryCase(
        id="RC-ERR",
        payment_id=payment.id,
        customer_id=payment.customer_id,
        customer_name="Test",
        amount_at_risk=payment.amount,
        risk_level="low",
        failure_category="temporary_gateway_failure",
        recommended_action="retry_payment",
        reason="test",
        evidence={},
        retry_count=0,
        max_retries=2,
        recovery_status="pending",
        action_status="eligible",
    )
    db_session.add(case)
    db_session.commit()

    def _boom(db, case_arg):
        raise RuntimeError("simulated unexpected failure")

    monkeypatch.setattr(batch_executor, "execute_recovery", _boom)

    result = run_batch_recovery(db_session)

    assert result["errored"] == 1
    assert result["escalated"] == 0
    assert result["attempted"] == 0

    db_session.refresh(case)
    assert case.recovery_status == "pending"
