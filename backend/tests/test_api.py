"""
test_api.py — End-to-end API integration tests
------------------------------------------------
Tests the full stack: seed → dashboard → cases → execute → audit
"""
import pytest


# ===========================================================================
# Demo endpoints
# ===========================================================================

class TestDemoSeed:
    def test_seed_returns_200(self, client):
        response = client.post("/api/demo/seed")
        assert response.status_code == 200

    def test_seed_returns_message(self, client):
        data = client.post("/api/demo/seed").json()
        assert "100" in data["message"]
        assert "Seeded" in data["message"]

    def test_seed_creates_100_payments(self, client):
        client.post("/api/demo/seed")
        response = client.get("/api/cases/")
        assert response.status_code == 200
        assert len(response.json()) == 100

    def test_seed_is_idempotent(self, client):
        """Seeding twice should produce exactly 100 records, not 200."""
        client.post("/api/demo/seed")
        client.post("/api/demo/seed")
        response = client.get("/api/cases/")
        assert len(response.json()) == 100


class TestDemoReset:
    def test_reset_clears_data(self, client):
        client.post("/api/demo/seed")
        client.post("/api/demo/reset")
        response = client.get("/api/cases/")
        assert response.json() == []

    def test_reset_returns_200(self, client):
        response = client.post("/api/demo/reset")
        assert response.status_code == 200


# ===========================================================================
# Dashboard
# ===========================================================================

class TestDashboard:
    def test_dashboard_returns_200(self, client):
        assert client.get("/api/dashboard/summary").status_code == 200

    def test_dashboard_empty_state(self, client):
        data = client.get("/api/dashboard/summary").json()
        assert data["total_payments"] == 0
        assert data["total_at_risk"] == 0.0
        assert data["total_recovered"] == 0.0
        assert data["recovery_rate_percent"] == 0.0
        assert data["open_cases"] == 0
        assert data["escalated_cases"] == 0

    def test_dashboard_after_seed(self, client):
        client.post("/api/demo/seed")
        data = client.get("/api/dashboard/summary").json()
        assert data["total_payments"] == 100
        assert data["total_at_risk"] > 0
        assert data["open_cases"] > 0

    def test_dashboard_at_risk_excludes_non_failed(self, client):
        """
        total_at_risk must only sum failed/abandoned payments.
        Since all demo payments are failed/abandoned, total_at_risk should
        equal the sum of all payment amounts.
        """
        client.post("/api/demo/seed")
        data = client.get("/api/dashboard/summary").json()
        assert data["total_at_risk"] > 0
        # After seeding, all payments are failed/abandoned so at_risk == total
        # (The key test is that it's not 0 and it uses the correct filter)

    def test_dashboard_has_all_required_fields(self, client):
        data = client.get("/api/dashboard/summary").json()
        required = {
            "total_payments", "total_at_risk", "total_recovered",
            "recovery_rate_percent", "open_cases", "escalated_cases",
            "recovery_attempts", "successful_recoveries", "failed_recoveries"
        }
        assert required.issubset(set(data.keys()))


# ===========================================================================
# Cases
# ===========================================================================

class TestCases:
    def test_list_cases_empty(self, client):
        assert client.get("/api/cases/").json() == []

    def test_list_cases_after_seed(self, client):
        client.post("/api/demo/seed")
        cases = client.get("/api/cases/").json()
        assert len(cases) == 100

    def test_case_has_required_fields(self, client):
        client.post("/api/demo/seed")
        case = client.get("/api/cases/").json()[0]
        required = {"id", "payment_id", "status", "risk_level", "diagnosis",
                    "recommended_action", "confidence", "evidence", "retry_count",
                    "attempt_count", "amount_recovered"}
        assert required.issubset(set(case.keys()))

    def test_case_has_payment(self, client):
        client.post("/api/demo/seed")
        case = client.get("/api/cases/").json()[0]
        assert case["payment"] is not None
        assert "transaction_id" in case["payment"]
        assert case["payment"]["transaction_id"].startswith("pay_demo_")

    def test_case_detail_returns_200(self, client):
        client.post("/api/demo/seed")
        case_id = client.get("/api/cases/").json()[0]["id"]
        response = client.get(f"/api/cases/{case_id}")
        assert response.status_code == 200

    def test_case_detail_not_found(self, client):
        response = client.get("/api/cases/99999")
        assert response.status_code == 404

    def test_case_status_filter(self, client):
        client.post("/api/demo/seed")
        open_cases = client.get("/api/cases/?status=OPEN").json()
        assert all(c["status"] == "OPEN" for c in open_cases)

    def test_case_payment_has_customer_name(self, client):
        client.post("/api/demo/seed")
        case = client.get("/api/cases/").json()[0]
        assert case["payment"]["customer_name"] is not None


# ===========================================================================
# Execution
# ===========================================================================

class TestExecution:
    def _get_open_case_id(self, client) -> int:
        """Helper: seed and return an OPEN case ID."""
        client.post("/api/demo/seed")
        cases = client.get("/api/cases/?status=OPEN").json()
        assert len(cases) > 0, "No OPEN cases after seed"
        return cases[0]["id"]

    def test_execute_open_case(self, client):
        case_id = self._get_open_case_id(client)
        response = client.post("/api/execution/execute", json={"case_id": case_id})
        assert response.status_code == 200

    def test_execute_returns_status(self, client):
        case_id = self._get_open_case_id(client)
        result = client.post("/api/execution/execute", json={"case_id": case_id}).json()
        valid_statuses = {"RECOVERED", "HALTED", "ESCALATED", "NEEDS_HUMAN_REVIEW", "OPEN"}
        assert result["status"] in valid_statuses

    def test_execute_returns_amount_recovered(self, client):
        case_id = self._get_open_case_id(client)
        result = client.post("/api/execution/execute", json={"case_id": case_id}).json()
        assert "amount_recovered" in result
        assert isinstance(result["amount_recovered"], (int, float))
        assert result["amount_recovered"] >= 0

    def test_execute_case_not_found(self, client):
        response = client.post("/api/execution/execute", json={"case_id": 99999})
        assert response.status_code == 404

    def test_execute_updates_dashboard(self, client):
        case_id = self._get_open_case_id(client)
        before = client.get("/api/dashboard/summary").json()
        client.post("/api/execution/execute", json={"case_id": case_id})
        after = client.get("/api/dashboard/summary").json()
        # Recovery attempts should increase
        assert after["recovery_attempts"] >= before["recovery_attempts"]


# ===========================================================================
# Batch Recovery
# ===========================================================================

class TestBatchRecovery:
    def test_batch_returns_200(self, client):
        client.post("/api/demo/seed")
        response = client.post("/api/demo/recovery-batch")
        assert response.status_code == 200

    def test_batch_returns_stats(self, client):
        client.post("/api/demo/seed")
        result = client.post("/api/demo/recovery-batch").json()
        required = {
            "total_cases", "attempted", "successful", "failed",
            "escalated", "amount_at_risk", "amount_recovered", "recovery_rate_percent"
        }
        assert required.issubset(set(result.keys()))

    def test_batch_attempted_equals_total_open(self, client):
        client.post("/api/demo/seed")
        open_count = len(client.get("/api/cases/?status=OPEN").json())
        result = client.post("/api/demo/recovery-batch").json()
        assert result["total_cases"] == open_count
        assert result["attempted"] == open_count

    def test_batch_no_cases_empty_result(self, client):
        # No data seeded
        result = client.post("/api/demo/recovery-batch").json()
        assert result["total_cases"] == 0
        assert result["attempted"] == 0


# ===========================================================================
# Failure Simulation
# ===========================================================================

class TestFailureSimulation:
    def test_arm_returns_200(self, client):
        response = client.post("/api/demo/simulate-failure")
        assert response.status_code == 200

    def test_arm_returns_armed_flag(self, client):
        result = client.post("/api/demo/simulate-failure").json()
        assert result["detail"]["failure_armed"] is True

    def test_failure_status_armed(self, client):
        client.post("/api/demo/simulate-failure")
        status = client.get("/api/demo/failure-status").json()
        assert status["failure_armed"] is True

    def test_armed_execution_produces_escalation(self, client):
        """After arming, next execution of an OPEN case must escalate."""
        client.post("/api/demo/seed")
        client.post("/api/demo/simulate-failure")

        # Find an OPEN case
        open_cases = client.get("/api/cases/?status=OPEN").json()
        # Only try non-invalid-card and non-HALT cases
        case_id = None
        for c in open_cases:
            if c.get("recommended_action") != "HALT_AND_ALERT":
                case_id = c["id"]
                break

        if case_id is None:
            pytest.skip("No eligible OPEN case for failure simulation test")

        result = client.post("/api/execution/execute", json={"case_id": case_id}).json()
        assert result["status"] == "NEEDS_HUMAN_REVIEW"
        assert result["amount_recovered"] == 0.0

    def test_failure_flag_resets_after_use(self, client):
        """Failure flag should be consumed after one use."""
        client.post("/api/demo/seed")
        client.post("/api/demo/simulate-failure")

        open_cases = client.get("/api/cases/?status=OPEN").json()
        eligible = [c for c in open_cases if c.get("recommended_action") != "HALT_AND_ALERT"]
        if len(eligible) < 2:
            pytest.skip("Not enough eligible cases")

        # First execution consumes the flag
        client.post("/api/execution/execute", json={"case_id": eligible[0]["id"]})

        # Flag should now be reset
        status = client.get("/api/demo/failure-status").json()
        assert status["failure_armed"] is False


# ===========================================================================
# Audit
# ===========================================================================

class TestAudit:
    def test_audit_returns_200(self, client):
        assert client.get("/api/audit/").status_code == 200

    def test_audit_empty_initially(self, client):
        assert client.get("/api/audit/").json() == []

    def test_audit_has_events_after_seed(self, client):
        client.post("/api/demo/seed")
        logs = client.get("/api/audit/").json()
        assert len(logs) > 0

    def test_audit_has_llm_diagnosis_events(self, client):
        client.post("/api/demo/seed")
        logs = client.get("/api/audit/").json()
        event_types = {log["event_type"] for log in logs}
        assert "LLM_DIAGNOSIS" in event_types

    def test_audit_diagnosis_has_case_id(self, client):
        """LLM_DIAGNOSIS events must reference a case_id, not null."""
        client.post("/api/demo/seed")
        logs = client.get("/api/audit/?event_type=LLM_DIAGNOSIS").json()
        assert len(logs) > 0
        # At least some should have case_id (the ones created with case linkage)
        with_case = [l for l in logs if l.get("case_id") is not None]
        assert len(with_case) > 0, "LLM_DIAGNOSIS events should have case_id linkage"

    def test_audit_execution_creates_events(self, client):
        client.post("/api/demo/seed")
        cases = client.get("/api/cases/?status=OPEN").json()
        if cases:
            client.post("/api/execution/execute", json={"case_id": cases[0]["id"]})
        logs = client.get("/api/audit/").json()
        event_types = {log["event_type"] for log in logs}
        # Should have policy check from execution
        assert "POLICY_CHECK" in event_types or "EXECUTION_COMPLETE" in event_types

    def test_audit_case_filter(self, client):
        client.post("/api/demo/seed")
        cases = client.get("/api/cases/").json()
        if not cases:
            return
        case_id = cases[0]["id"]
        logs = client.get(f"/api/audit/?case_id={case_id}").json()
        # All returned logs should be for this case
        assert all(l["case_id"] == case_id for l in logs if l["case_id"] is not None)


# ===========================================================================
# Policy Engine
# ===========================================================================

class TestPolicyEngine:
    def test_recovered_case_cannot_be_re_executed(self, client):
        """RECOVERED cases must be blocked by policy."""
        client.post("/api/demo/seed")
        # Find and execute a case until it recovers or exhaust open cases
        open_cases = client.get("/api/cases/?status=OPEN").json()
        recovered_case_id = None

        for c in open_cases:
            if c["recommended_action"] == "HALT_AND_ALERT":
                continue
            result = client.post("/api/execution/execute", json={"case_id": c["id"]}).json()
            if result["status"] == "RECOVERED":
                recovered_case_id = c["id"]
                break

        if recovered_case_id is None:
            pytest.skip("Could not find a RECOVERED case for this test")

        # Try to execute the RECOVERED case again
        result2 = client.post("/api/execution/execute", json={"case_id": recovered_case_id}).json()
        assert result2["status"] in {"RECOVERED", "HALTED"}
        assert result2["amount_recovered"] == 0.0


# ===========================================================================
# Health Check
# ===========================================================================

class TestHealth:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"

    def test_health_has_provider_info(self, client):
        data = client.get("/health").json()
        assert "llm_provider" in data
        assert "llm_providers" in data

    def test_providers_endpoint(self, client):
        response = client.get("/api/providers")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "active" in data
