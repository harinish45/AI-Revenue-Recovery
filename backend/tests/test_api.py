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
