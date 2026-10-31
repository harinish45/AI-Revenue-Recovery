from fastapi.testclient import TestClient


def test_recovery_analytics_dashboard_endpoint(client: TestClient):
    client.post("/api/demo/seed")

    response = client.get("/api/dashboard/recovery-analytics")
    assert response.status_code == 200
    data = response.json()

    assert "recovered_mrr" in data
    assert "active_dunning_cases" in data
    assert "dunning_cases_by_stage" in data
    assert "win_rate_by_retry_attempt" in data
    assert "churn_risk_distribution" in data
    assert "gateway_breakdown" in data
    assert "net_revenue_saved" in data

    # Check dunning stages exist
    stages = data["dunning_cases_by_stage"]
    assert "grace_period" in stages
    assert "soft_retry_scheduled" in stages

    # Check retry attempts structure
    attempts = data["win_rate_by_retry_attempt"]
    assert "attempt_1" in attempts
    assert "attempt_2" in attempts
    assert "win_rate" in attempts["attempt_1"]

    # Check gateway breakdown
    gateways = data["gateway_breakdown"]
    assert "razorpay" in gateways
    assert "stripe" in gateways


def test_dunning_case_state_and_transition(client: TestClient):
    client.post("/api/demo/seed")
    cases = client.get("/api/cases").json()["items"]
    case_id = cases[0]["id"]

    # Get state
    response = client.get(f"/api/dunning/{case_id}/state")
    assert response.status_code == 200
    state_data = response.json()
    assert state_data["case_id"] == case_id
    assert "current_state" in state_data

    # Valid transition to card_update_requested
    transition_resp = client.post(
        f"/api/dunning/{case_id}/transition",
        json={"target_state": "card_update_requested", "reason": "Customer updated card requested"},
    )
    assert transition_resp.status_code == 200
    assert transition_resp.json()["current_state"] == "card_update_requested"


def test_dunning_notifications_dispatch_and_preview(client: TestClient):
    client.post("/api/demo/seed")
    cases = client.get("/api/cases").json()["items"]
    case_id = cases[0]["id"]

    # Preview notification
    preview_resp = client.post(
        "/api/dunning/notifications/preview",
        json={
            "template": "grace_period",
            "locale": "es",
            "context": {"customer_name": "Carlos", "amount": "50.00"},
        },
    )
    assert preview_resp.status_code == 200
    assert "Carlos" in preview_resp.json()["body"]

    # Send notification
    send_resp = client.post(
        f"/api/dunning/{case_id}/notifications",
        json={
            "template": "grace_period",
            "sequence_step": 1,
            "locale": "en",
        },
    )
    assert send_resp.status_code == 200
    notif = send_resp.json()
    assert notif["case_id"] == case_id
    assert notif["status"] == "delivered"

    # List notifications
    list_resp = client.get(f"/api/dunning/{case_id}/notifications")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1


def test_churn_scoring_endpoints(client: TestClient):
    client.post("/api/demo/seed")
    cases = client.get("/api/cases").json()["items"]
    case_id = cases[0]["id"]

    # Test case churn risk
    score_resp = client.get(f"/api/cases/{case_id}/churn-risk")
    assert score_resp.status_code == 200
    data = score_resp.json()
    assert 0.0 <= data["recovery_probability"] <= 100.0
    assert 0.0 <= data["churn_risk_score"] <= 100.0
    assert data["risk_tier"] in ("low", "medium", "high", "critical")
    assert data["recommended_strategy"]
    assert len(data["key_factors"]) > 0

    # Test dynamic scoring evaluate
    eval_resp = client.post(
        "/api/scoring/evaluate",
        json={
            "tenure_months": 18,
            "decline_code": "insufficient_funds",
            "amount": 2500.0,
            "total_payments": 18,
            "success_rate": 94.4,
            "previous_failures": 1,
            "attempt_number": 1,
        },
    )
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["recovery_probability"] > 50.0
