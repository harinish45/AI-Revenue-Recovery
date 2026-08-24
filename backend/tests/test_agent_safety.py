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


def test_execution_is_idempotent_and_response_has_security_headers(client: TestClient, session):
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
    assert session.query(Execution).filter(Execution.case_id == case_id).count() == 1
    assert session.query(AuditSeal).count() > 0
    assert first.headers["x-content-type-options"] == "nosniff"
    assert first.headers["x-request-id"]


def test_pagination_is_bounded(client: TestClient):
    response = client.get("/api/cases/?limit=1001")
    assert response.status_code == 422
