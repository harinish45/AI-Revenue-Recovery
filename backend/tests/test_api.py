from fastapi.testclient import TestClient

def test_seed_and_dashboard(client):
    response = client.post("/api/demo/seed")
    assert response.status_code == 200
    assert response.json()["created_records"] == 100
    
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_transactions"] == 100
    assert data["failed_payments"] == 20

def test_execution_and_policy(client):
    client.post("/api/demo/seed")
    
    cases = client.get("/api/recovery/cases").json()
    assert len(cases["items"]) > 0
    case_id = cases["items"][0]["id"]
    
    response = client.post(f"/api/recovery/cases/{case_id}/execute")
    assert response.status_code == 200
    assert response.json()["case_id"] == case_id
    
    logs = client.get("/api/recovery/audit").json()
    assert len(logs["items"]) > 0

def test_batch_recovery(client):
    client.post("/api/demo/seed")
    response = client.post("/api/demo/recovery-batch")
    assert response.status_code == 200
    data = response.json()
    assert data["processed"] > 0

def test_simulate_failure(client):
    client.post("/api/demo/seed")
    
    response = client.post("/api/demo/simulate-failure")
    assert response.status_code == 200
    case_id = response.json()["case_id"]
    
    response = client.post(f"/api/recovery/cases/{case_id}/execute")
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
