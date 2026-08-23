from fastapi.testclient import TestClient

def test_seed_data(client):
    response = client.post("/api/demo/seed")
    assert response.status_code == 200
    assert "Successfully seeded" in response.json()["message"]

def test_dashboard_summary(client):
    client.post("/api/demo/seed")
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_at_risk" in data
    assert data["total_payments"] == 100

def test_batch_process(client):
    client.post("/api/demo/seed")
    response = client.post("/api/demo/recovery-batch")
    assert response.status_code == 200
    data = response.json()
    assert "total_cases" in data
    assert "amount_recovered" in data

def test_list_cases(client):
    client.post("/api/demo/seed")
    response = client.get("/api/cases/")
    assert response.status_code == 200
    assert len(response.json()) == 100

def test_execute_recovery(client):
    client.post("/api/demo/seed")
    cases = client.get("/api/cases/").json()
    case_id = cases[0]["id"]
    
    response = client.post("/api/execution/execute", json={"case_id": case_id})
    assert response.status_code == 200
    assert response.json()["status"] in ["RECOVERED", "ESCALATED", "needs_human_review", "HALTED"]

def test_audit_logs(client):
    client.post("/api/demo/seed")
    response = client.get("/api/audit/")
    assert response.status_code == 200
    assert len(response.json()) > 0

def test_new_failure_codes_present(client):
    client.post("/api/demo/seed")
    cases = client.get("/api/cases/").json()
    failure_codes = [c["payment"]["failure_code"] for c in cases if c.get("payment")]
    new_codes = {"3ds_authentication_failed", "upi_pin_retry_limit", "mandate_revoked"}
    # At least one of the new codes must be present in 100 cases
    assert len(new_codes.intersection(set(failure_codes))) > 0

def test_llm_provider_chain_fallback():
    from app.services.llm_provider_chain import chain
    
    # Test mandate_revoked
    payment_data = {"failure_code": "mandate_revoked", "amount": 1000}
    decision = chain.get_decision(payment_data, {})
    assert decision.decision == "CUSTOMER_REMINDER"
    
    # Test upi_pin_retry_limit
    payment_data = {"failure_code": "upi_pin_retry_limit", "amount": 500}
    decision = chain.get_decision(payment_data, {})
    assert decision.decision == "RETRY_PAYMENT"
    
    # Test 3ds_authentication_failed
    payment_data = {"failure_code": "3ds_authentication_failed", "amount": 2000}
    decision = chain.get_decision(payment_data, {})
    assert decision.decision == "RETRY_PAYMENT"

def test_invalid_card_halts_execution(client):
    client.post("/api/demo/seed")
    cases = client.get("/api/cases/").json()
    
    # Find an invalid_card case
    invalid_case = next((c for c in cases if c.get("payment") and c["payment"]["failure_code"] == "invalid_card"), None)
    if invalid_case:
        response = client.post("/api/execution/execute", json={"case_id": invalid_case["id"]})
        assert response.status_code == 200
        assert response.json()["status"] == "HALTED"
