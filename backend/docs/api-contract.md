# RecoverAI API Contract

## Endpoints

### Demo
- `POST /api/demo/seed`: Seeds 100 synthetic payments and generates recovery cases.
- `POST /api/demo/reset`: Clears the database.

### Dashboard
- `GET /api/dashboard/summary`: Returns metrics (total_payments, total_at_risk, total_recovered, recovery_rate_percent, open_cases, escalated_cases).

### Cases
- `GET /api/cases/`: Lists all recovery cases.
- `GET /api/cases/{case_id}`: Gets details for a specific case.

### Execution
- `POST /api/execution/execute`: Executes recovery for a case. Body: `{"case_id": int}`.
  - Returns status, action, result, and amount_recovered.
  - Enforces policy limits (max retries, max amount, halted states).

### Audit
- `GET /api/audit/`: Lists all audit logs with timestamps and JSON details.
