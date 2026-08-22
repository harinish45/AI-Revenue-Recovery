from fastapi.testclient import TestClient

def test_seed_and_dashboard(client):
    response = client.post("/api/demo/seed")
    assert response.status_code == 200
    assert "100 payments" in response.json()["message"]
    
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_payments"] == 100
    assert data["total_at_risk"] > 0

def test_execution_and_policy(client):
    client.post("/api/demo/seed")
    
    cases = client.get("/api/cases/").json()
    case_id = cases[0]["id"]
    
    response = client.post("/api/execution/execute", json={"case_id": case_id})
    assert response.status_code == 200
    
    logs = client.get("/api/audit/").json()
    assert len(logs) > 0
