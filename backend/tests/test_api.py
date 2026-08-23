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
    response = client.post("/api/execution/execute", json={"case_id": case_id})
    assert response.status_code == 200
    assert response.json()["case_id"] == case_id
    
    # Test standard path execution
    case_id_2 = cases["items"][1]["id"]
    response = client.post(f"/api/recovery/cases/{case_id_2}/execute")
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
    
    response = client.post("/api/execution/execute", json={"case_id": case_id})
    assert response.status_code == 200
    assert response.json()["status"] == "needs_human_review"
