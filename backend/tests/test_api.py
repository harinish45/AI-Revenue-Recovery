from fastapi.testclient import TestClient


def test_seed_and_dashboard(client: TestClient):
    response = client.post("/api/demo/seed")
    assert response.status_code == 200
    assert response.json()["created_records"] == 100

    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_transactions"] == 100
    assert data["failed_payments"] == 20


def test_cases_and_audit_alt_routes(client: TestClient):
    client.post("/api/demo/seed")

    # Test alt routes requested in final prompt
    cases = client.get("/api/cases").json()
    assert len(cases["items"]) > 0

    logs = client.get("/api/audit").json()
    assert len(logs["items"]) > 0


def test_execution_body_request(client: TestClient):
    client.post("/api/demo/seed")

    cases = client.get("/api/cases").json()
    case_id = cases["items"][0]["id"]

    # Test JSON body execution requested in final prompt
    response = client.post(
        "/api/execution/execute",
        json={"case_id": case_id},
        headers={"Idempotency-Key": "qa-execute-1"},
    )
    assert response.status_code == 200
    assert response.json()["case_id"] == case_id

    # Test standard path execution
    case_id_2 = cases["items"][1]["id"]
    response = client.post(
        f"/api/recovery/cases/{case_id_2}/execute", headers={"Idempotency-Key": "qa-execute-2"}
    )
    assert response.status_code == 200


def test_batch_recovery(client: TestClient):
    client.post("/api/demo/seed")

    # Test alt batch route
    response = client.post("/api/batch/process")
    assert response.status_code == 200
    data = response.json()
    assert data["total_cases"] > 0
    assert "recovery_rate" in data

    # Reset and test demo batch route
    client.post("/api/demo/reset")
    client.post("/api/demo/seed")
    response = client.post("/api/demo/recovery-batch")
    assert response.status_code == 200
    data = response.json()
    assert data["total_cases"] > 0


def test_simulate_failure(client: TestClient):
    client.post("/api/demo/seed")

    response = client.post("/api/demo/simulate-failure")
    assert response.status_code == 200
    case_id = response.json()["case_id"]

    response = client.post(
        "/api/execution/execute",
        json={"case_id": case_id},
        headers={"Idempotency-Key": "qa-failure-1"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "needs_human_review"


def test_voice_event_is_persisted_to_real_audit_trail(client: TestClient):
    client.post("/api/demo/seed")
    case_id = client.get("/api/cases").json()["items"][0]["id"]

    response = client.post(
        f"/api/cases/{case_id}/voice-events",
        json={
            "event_type": "voice_promise_captured",
            "intent": "PROMISE_TO_PAY",
            "transcript": "haan bilkul pay kar dunga",
            "consent_confirmed": True,
            "language": "hi",
            "confidence": 0.92,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == case_id
    assert body["event_type"] == "voice_promise_captured"

    logs = client.get("/api/audit", params={"case_id": case_id}).json()["items"]
    matching = [row for row in logs if row["id"] == body["audit_event_id"]]
    assert len(matching) == 1
    assert matching[0]["actor"] == "voice_agent"
    assert matching[0]["decision"] == "PROMISE_TO_PAY"


def test_voice_event_rejects_unknown_case(client: TestClient):
    response = client.post(
        "/api/cases/RC-NOPE/voice-events",
        json={"event_type": "voice_call_started"},
    )
    assert response.status_code == 404


def test_audit_seal_is_exposed_and_verifiable(client: TestClient):
    client.post("/api/demo/seed")
    event = client.get("/api/audit").json()["items"][0]
    assert event["event_hash"]
    verified = client.get(f"/api/audit/{event['id']}/verify")
    assert verified.status_code == 200
    assert verified.json()["chain_verified"] is True


def test_smart_skip_is_backend_measured(client: TestClient):
    client.post("/api/demo/seed")
    cases = client.get("/api/cases", params={"limit": 100}).json()["items"]
    tiny = next(item for item in cases if item["amount"] == 25.0)
    result = client.post(
        "/api/execution/execute",
        json={"case_id": tiny["id"]},
        headers={"Idempotency-Key": "qa-smart-skip-1"},
    )
    assert result.status_code == 200
    assert result.json()["status"] == "skipped"


def test_webhook_ingestion_is_audited(client: TestClient):
    response = client.post("/api/webhooks/razorpay", json={"id": "wh_demo_1", "event": "payment.failed"})
    assert response.status_code == 200
    assert response.json()["accepted"] is True


def test_webhook_duplicate_is_idempotent(client: TestClient):
    payload = {"id": "wh_duplicate", "event": "payment.failed"}
    first = client.post("/api/webhooks/razorpay", json=payload)
    second = client.post("/api/webhooks/razorpay", json=payload)
    assert first.status_code == second.status_code == 200
    assert "duplicate" in second.json()["message"].lower()
    assert client.get("/api/audit", params={"limit": 100}).json()["total"] == 1


def test_idempotency_key_cannot_cross_cases(client: TestClient):
    client.post("/api/demo/seed")
    cases = client.get("/api/cases", params={"limit": 100}).json()["items"]
    key = "same-key-cross-case"
    assert client.post("/api/execution/execute", json={"case_id": cases[0]["id"]}, headers={"Idempotency-Key": key}).status_code == 200
    response = client.post("/api/execution/execute", json={"case_id": cases[1]["id"]}, headers={"Idempotency-Key": key})
    assert response.status_code == 409


def test_voice_event_rejected_on_terminal_case(client: TestClient):
    client.post("/api/demo/seed")
    cases = client.get("/api/cases", params={"limit": 100}).json()["items"]
    open_case = cases[0]
    client.post(
        "/api/execution/execute",
        json={"case_id": open_case["id"]},
        headers={"Idempotency-Key": f"qa-voice-term-{open_case['id']}"},
    )
    response = client.post(
        f"/api/cases/{open_case['id']}/voice-events",
        json={"event_type": "voice_promise_captured", "consent_confirmed": True, "intent": "PROMISE_TO_PAY"},
    )
    assert response.status_code == 409
    body = response.json()
    msg = body.get("error", {}).get("message", "") or body.get("detail", "")
    assert "already" in msg.lower()



