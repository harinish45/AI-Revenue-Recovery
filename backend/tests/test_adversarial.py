"""Adversarial regression suite: proves the safety boundaries hold under abuse."""

from datetime import timedelta

from fastapi.testclient import TestClient

from app.config import settings as app_settings
from app.models import AuditLog, Customer, Payment, RecoveryCase
from app.utils.time import utcnow


def _seed(client: TestClient):
    assert client.post("/api/demo/seed").status_code == 200
    return client.get("/api/cases", params={"limit": 100}).json()["items"]


def _detail(response) -> str:
    """Read the error message from either the structured envelope or `detail`."""
    body = response.json()
    return body.get("detail") or body.get("error", {}).get("message", "")


def _execute(client: TestClient, case_id: str, key: str = "adv-key"):
    return client.post(
        "/api/execution/execute",
        json={"case_id": case_id},
        headers={"Idempotency-Key": f"{key}-{case_id}"},
    )


def test_production_mode_disables_demo_endpoints(client: TestClient, monkeypatch):
    monkeypatch.setattr(app_settings, "APP_ENV", "production")
    for route in ("/api/demo/reset", "/api/demo/seed", "/api/demo/recovery-batch", "/api/demo/simulate-failure"):
        response = client.post(route)
        assert response.status_code == 404, route


def test_demo_token_is_enforced_when_configured(client: TestClient, monkeypatch):
    monkeypatch.setattr(app_settings, "DEMO_API_TOKEN", "s3cret")
    assert client.post("/api/demo/reset").status_code == 403
    assert client.post("/api/demo/reset", headers={"X-Demo-Token": "wrong"}).status_code == 403
    assert client.post("/api/demo/reset", headers={"X-Demo-Token": "s3cret"}).status_code == 200


def test_execution_requires_idempotency_key(client: TestClient):
    _seed(client)
    cases = client.get("/api/cases", params={"limit": 100}).json()["items"]
    response = client.post("/api/execution/execute", json={"case_id": cases[0]["id"]})
    assert response.status_code == 400
    assert "Idempotency-Key" in _detail(response)


def test_failure_simulation_cannot_bypass_amount_limit(client: TestClient, db_session):
    _seed(client)
    client.post("/api/demo/simulate-failure")

    customer = Customer(id="cus_adv", name="Adv", email="a@b.c", phone="+911234567890")
    payment = Payment(id="pay_adv_big", customer_id=customer.id, amount=999999.0, status="failed", failure_reason="Gateway timeout")
    case = RecoveryCase(
        id="RC-ADVBIG", payment_id=payment.id, customer_id=customer.id, customer_name="Adv",
        amount_at_risk=999999.0, risk_level="low", failure_category="temporary_gateway_failure",
        recommended_action="retry_payment", reason="adv", evidence={}, retry_count=0,
        max_retries=2, recovery_status="pending",
    )
    db_session.add_all([customer, payment, case])
    db_session.commit()

    response = _execute(client, "RC-ADVBIG", "adv-amount")
    assert response.status_code == 200
    body = response.json()
    # The armed failure must NOT be consumed: the amount policy blocks first.
    assert body["status"] == "needs_human_review"
    assert "Amount exceeds" in body["message"]
    assert db_session.query(RecoveryCase).filter(RecoveryCase.id == "RC-ADVBIG").one().recovery_status == "needs_human_review"


def test_failure_simulation_cannot_execute_terminal_case(client: TestClient, db_session):
    _seed(client)
    client.post("/api/demo/simulate-failure")

    customer = Customer(id="cus_adv_done", name="Done", email="d@b.c", phone="+919876543210")
    payment = Payment(id="pay_adv_done", customer_id=customer.id, amount=1200.0, status="success", failure_reason="Gateway timeout")
    case = RecoveryCase(
        id="RC-ADVDONE", payment_id=payment.id, customer_id=customer.id, customer_name="Done",
        amount_at_risk=1200.0, risk_level="low", failure_category="temporary_gateway_failure",
        recommended_action="retry_payment", reason="adv", evidence={}, retry_count=1,
        max_retries=2, recovery_status="recovered", recovered_amount=1200.0,
    )
    db_session.add_all([customer, payment, case])
    db_session.commit()

    response = _execute(client, "RC-ADVDONE", "adv-terminal")
    assert response.status_code == 200
    body = response.json()
    assert "terminal state" in body["message"].lower()
    # The armed failure must not be consumed by a terminal case, and a
    # recovered case must stay recovered.
    assert db_session.query(RecoveryCase).filter(RecoveryCase.id == "RC-ADVDONE").one().recovery_status == "recovered"


def test_missing_payment_record_escalates_without_server_error(client: TestClient, db_session):
    _seed(client)
    case = RecoveryCase(
        id="RC-ADVNOPAY", payment_id="pay_missing", customer_id="cus_demo_1",
        customer_name="Ghost", amount_at_risk=1500.0, risk_level="low",
        failure_category="temporary_gateway_failure", recommended_action="retry_payment",
        reason="adv", evidence={}, retry_count=0, max_retries=2, recovery_status="pending",
    )
    db_session.add(case)
    db_session.commit()

    response = _execute(client, "RC-ADVNOPAY", "adv-nopay")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_human_review"
    assert "missing" in body["message"].lower()
    assert body["audit_event_id"].startswith("AUD-")
    assert body["recovered_amount"] == 0.0


def test_manual_only_case_is_blocked(client: TestClient, db_session):
    _seed(client)
    case = db_session.query(RecoveryCase).filter(RecoveryCase.recovery_status == "pending").first()
    case.action_status = "manual_only"
    db_session.commit()

    response = _execute(client, case.id, "adv-manual")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("needs_human_review", "blocked")
    assert "action_status" in body["message"]


def test_case_payment_amount_mismatch_is_rejected(client: TestClient, db_session):
    _seed(client)
    case = db_session.query(RecoveryCase).filter(RecoveryCase.recovery_status == "pending").first()
    payment = db_session.query(Payment).filter(Payment.id == case.payment_id).one()
    case.amount_at_risk = payment.amount + 500.0
    db_session.commit()

    response = _execute(client, case.id, "adv-mismatch")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("needs_human_review", "blocked")
    assert "reconcile" in body["message"].lower()


def test_execute_response_returns_verifiable_audit_id(client: TestClient):
    items = _seed(client)
    case_id = next(c["id"] for c in items if c["recommended_action"] == "retry_payment")
    response = _execute(client, case_id, "adv-audit")
    assert response.status_code == 200
    audit_id = response.json()["audit_event_id"]
    assert audit_id.startswith("AUD-")
    verified = client.get(f"/api/audit/{audit_id}/verify")
    assert verified.status_code == 200
    assert verified.json()["chain_verified"] is True


def test_payment_link_does_not_claim_revenue_until_confirmed(client: TestClient, db_session):
    items = _seed(client)
    case_id = next(c["id"] for c in items if c["recommended_action"] == "payment_link")
    response = _execute(client, case_id, "adv-link")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "awaiting_payment"
    assert body["recovered_amount"] == 0.0

    db_session.expire_all()
    case = db_session.query(RecoveryCase).filter(RecoveryCase.id == case_id).one()
    assert case.recovery_status == "awaiting_payment"
    assert case.recovered_amount == 0.0

    confirmed = client.post(f"/api/execution/cases/{case_id}/confirm-payment")
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "recovered"
    assert confirmed.json()["recovered_amount"] == case.amount_at_risk


def test_awaiting_payment_case_cannot_execute_again(client: TestClient):
    items = _seed(client)
    case_id = next(c["id"] for c in items if c["recommended_action"] == "payment_link")
    first = _execute(client, case_id, "adv-twice")
    assert first.json()["status"] == "awaiting_payment"
    second = _execute(client, case_id, "adv-twice-2")
    assert second.status_code == 200
    assert "terminal state" in second.json()["message"].lower()


def test_retry_window_rejects_immediate_second_retry(client: TestClient, db_session):
    items = _seed(client)
    case_id = next(c["id"] for c in items if c["recommended_action"] == "retry_payment")
    first = _execute(client, case_id, "adv-retry-1")
    assert first.json()["status"] == "recovered"  # direct gateway retry confirms

    db_session.expire_all()
    case = db_session.query(RecoveryCase).filter(RecoveryCase.id == case_id).one()
    case.recovery_status = "failed"
    case.updated_at = utcnow().replace(tzinfo=None) - timedelta(hours=1)
    db_session.commit()

    response = _execute(client, case_id, "adv-retry-2")
    assert response.status_code == 200
    assert "Retry window" in response.json()["message"]


def test_voice_promise_without_explicit_consent_is_rejected(client: TestClient):
    items = _seed(client)
    case_id = items[0]["id"]
    for payload in (
        {"event_type": "voice_promise_captured"},
        {"event_type": "voice_promise_captured", "consent_confirmed": False},
    ):
        response = client.post(f"/api/cases/{case_id}/voice-events", json=payload)
        assert response.status_code == 400
        assert "consent" in _detail(response).lower()


def test_voice_transcript_size_is_bounded(client: TestClient):
    items = _seed(client)
    response = client.post(
        f"/api/cases/{items[0]['id']}/voice-events",
        json={"event_type": "voice_call_started", "transcript": "x" * 2001},
    )
    assert response.status_code == 422


def test_webhook_rejects_unknown_event_missing_id_and_oversize(client: TestClient):
    assert client.post("/api/webhooks/razorpay", json={"id": "wh_x", "event": "payment.refund.made_up"}).status_code == 400
    assert client.post("/api/webhooks/razorpay", json={"event": "payment.failed"}).status_code == 400
    assert client.post("/api/webhooks/razorpay", json={"id": "wh_big", "event": "payment.failed", "blob": "y" * 300_000}).status_code == 413
    assert client.post("/api/webhooks/razorpay", content=b"not json", headers={"Content-Type": "application/json"}).status_code == 400


def test_webhook_stale_event_is_rejected(client: TestClient):
    stale = (utcnow() - timedelta(seconds=10_000)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    response = client.post(
        "/api/webhooks/razorpay",
        json={"id": "wh_stale_1", "event": "payment.failed", "timestamp": stale},
    )
    assert response.status_code == 400
    assert "stale" in _detail(response).lower()


def test_audit_chain_verification_detects_tampering(client: TestClient, db_session):
    _seed(client)
    assert client.get("/api/audit/chain/verify").json()["valid"] is True

    target = db_session.query(AuditLog).first()
    target.reason = "TAMPERED BY ATTACKER"
    db_session.commit()

    report = client.get("/api/audit/chain/verify").json()
    assert report["valid"] is False
    tampered = [e for e in report["events"] if e["audit_id"] == target.id]
    assert tampered and tampered[0]["valid"] is False


def test_batch_isolates_poisoned_cases(client: TestClient, db_session, monkeypatch):
    _seed(client)
    case = db_session.query(RecoveryCase).filter(RecoveryCase.recovery_status == "pending").first()
    case.payment_id = "pay_does_not_exist_and_case_also_broken"
    db_session.commit()

    from app.services import recovery_executor

    original = recovery_executor._run_recovery

    def exploding(db, c):
        if c.id == case.id:
            raise RuntimeError("simulated crash")
        return original(db, c)

    monkeypatch.setattr(recovery_executor, "_run_recovery", exploding)
    response = client.post("/api/demo/recovery-batch")
    assert response.status_code == 200
    body = response.json()
    assert body["batch_id"].startswith("BATCH-")
    assert body["total_cases"] > 1


