from fastapi.testclient import TestClient

from app.models import AuditSeal, Execution
from app.services.recovery_agent import choose_intervention


def test_agent_returns_bounded_decision_contract():
    decision = choose_intervention("gateway timeout", 80)
    assert decision.action == "retry_payment"
    assert 0 <= decision.confidence <= 1
    assert decision.stopping_rules

    escalated = choose_intervention("invalid card", 80)
    assert escalated.action == "needs_human_review"
    assert "never retry automatically" in escalated.stopping_rules


def test_agent_confidence_is_a_function_of_customer_evidence_not_a_constant():
    """Two customers hitting the same failure category must not get identical
    confidence just because the reason text matches the same branch -- that
    would mean the "AI" is really a static lookup table. A clean-history
    customer should score higher than one with a track record of repeated
    failures and no successful payments."""
    clean_history = choose_intervention(
        "gateway timeout", success_rate=90, previous_failures=0, total_payments=6
    )
    troubled_history = choose_intervention(
        "gateway timeout", success_rate=0, previous_failures=5, total_payments=5
    )
    assert clean_history.confidence > troubled_history.confidence
    assert 0.55 <= troubled_history.confidence <= 0.99
    assert 0.55 <= clean_history.confidence <= 0.99

    # Same category, same evidence, same call -> same score (deterministic,
    # not random), but distinguishable from a second category's evidence-free
    # baseline call (default previous_failures/total_payments=0).
    baseline = choose_intervention("gateway timeout", success_rate=0)
    repeat_call = choose_intervention("gateway timeout", success_rate=0)
    assert baseline.confidence == repeat_call.confidence


def test_execution_is_idempotent_and_response_has_security_headers(client: TestClient, db_session):
    client.post("/api/demo/seed")
    cases = client.get("/api/cases/").json()["items"]
    case_id = next(c["id"] for c in cases if c["recommended_action"] != "needs_human_review")

    first = client.post(
        "/api/execution/execute",
        json={"case_id": case_id},
        headers={"Idempotency-Key": "demo-retry-001"},
    )
    second = client.post(
        "/api/execution/execute",
        json={"case_id": case_id},
        headers={"Idempotency-Key": "demo-retry-001"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert db_session.query(Execution).filter(Execution.case_id == case_id).count() == 1
    assert db_session.query(AuditSeal).count() > 0
    assert first.headers["x-content-type-options"] == "nosniff"
    assert first.headers["x-request-id"]


def test_pagination_is_bounded(client: TestClient):
    response = client.get("/api/cases", params={"limit": 1001})
    assert response.status_code == 422
