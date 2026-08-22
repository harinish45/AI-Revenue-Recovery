from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

client = TestClient(app)

def setup_module():
    Base.metadata.create_all(bind=engine)

def test_seed_data():
    response = client.post("/api/demo/seed")
    assert response.status_code == 200
    assert "Seeded 100" in response.json()["message"]

def test_dashboard_summary():
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_at_risk" in data
    assert data["total_at_risk"] > 0

def test_batch_process():
    response = client.post("/api/batch/process")
    assert response.status_code == 200
    assert "new recovery cases created" in response.json()["message"]

def test_list_cases():
    response = client.get("/api/cases/")
    assert response.status_code == 200
    assert len(response.json()) > 0

def test_execute_recovery():
    cases = client.get("/api/cases/").json()
    case_id = cases[0]["id"]
    response = client.post("/api/execution/execute", json={"case_id": case_id})
    assert response.status_code == 200
    assert response.json()["status"] in ["recovered", "nudged", "escalated"]

def test_audit_logs():
    response = client.get("/api/audit/")
    assert response.status_code == 200
    assert len(response.json()) > 0
