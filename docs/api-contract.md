# RecoverAI API Contract

## Base URL
`http://localhost:8000`

## Endpoints

### Demo Controls
- `POST /api/demo/seed`
  - Action: Wipes DB, generates 100 deterministic synthetic payments and recovery cases.
  - Response: `{"message": "Successfully seeded 100 payments and generated recovery cases."}`
- `POST /api/demo/reset`
  - Action: Wipes DB.
  - Response: `{"message": "Database reset complete."}`
- `POST /api/demo/recovery-batch`
  - Action: Executes recovery on all OPEN cases.
  - Response: `{"total_cases": int, "attempted": int, "successful": int, "failed": int, "escalated": int, "amount_at_risk": float, "amount_recovered": float, "recovery_rate": float}`
- `POST /api/demo/simulate-failure`
  - Action: Arms a deterministic flag so the NEXT execution fails gracefully and escalates.
  - Response: `{"status": "armed", "message": "Simulated gateway failure armed for the next recovery execute."}`

### Dashboard & Metrics
- `GET /api/dashboard/summary`
  - Response: `{"total_payments": int, "total_at_risk": float, "total_recovered": float, "recovery_rate_percent": float, "open_cases": int, "escalated_cases": int}`

### Cases
- `GET /api/cases/`
  - Response: Array of cases with nested payment details (including `customer_name` and `risk_level`).
- `GET /api/cases/{case_id}`
  - Response: Single case object.

### Execution
- `POST /api/execution/execute`
  - Body: `{"case_id": int}`
  - Response: `{"status": str, "action": str, "result": str, "amount_recovered": float}`
  - Note: If failure simulation is armed, returns `{"status": "needs_human_review", "recovered_amount": 0.0, "message": "..."}`

### Audit
- `GET /api/audit/`
  - Response: Array of audit logs linked to `case_id`.
