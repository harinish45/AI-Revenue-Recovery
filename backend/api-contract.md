# RecoverAI API Contract

## Base URL
`http://localhost:8000`

## Endpoints

### Dashboard
- `GET /api/dashboard/summary`
  - Returns revenue at risk, recovered amount, open/escalated cases, recovery rate.

### Cases
- `GET /api/cases/`
  - List all recovery cases.
- `GET /api/cases/{case_id}`
  - Get details of a specific recovery case.

### Execution
- `POST /api/execution/execute`
  - Body: `{"case_id": int}`
  - Diagnoses root cause, checks policies, and executes recovery intervention.

### Audit
- `GET /api/audit/`
  - List all audit logs.

### Batch
- `POST /api/batch/process`
  - Generates recovery cases for failed payments.

### Demo
- `POST /api/demo/seed`
  - Seeds 100 synthetic failed payment records.
- `POST /api/demo/reset`
  - Clears all data.
