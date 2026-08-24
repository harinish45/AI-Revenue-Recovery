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
  - Body: `{"case_id": "RC-..."}`
  - Optional `Idempotency-Key` header — replaying the same key returns the original result instead of re-executing.
  - Diagnoses root cause, checks policies, and executes recovery intervention.
  - Returns `409` if the case is already in a terminal state (`recovered`/`blocked`/`needs_human_review`) and no idempotency key was provided.

### Audit
- `GET /api/audit/`
  - List all audit logs.

### Batch
- `POST /api/batch/process`
  - Runs the recovery workflow for every pending, eligible case.

### Demo
- `POST /api/demo/seed`
  - Seeds 100 synthetic payments (mix of success/failed/abandoned) and derives recovery cases from the failed/abandoned ones.
- `POST /api/demo/reset`
  - Clears all data.

### Voice Agent
- `POST /api/cases/{case_id}/voice-events`
  - Body: `{"event_type": "voice_promise_captured", "intent": "PROMISE_TO_PAY", "transcript": "..."}`
  - `event_type` is one of `voice_call_started`, `voice_call_ended`, `voice_promise_captured`, `voice_dispute_raised`.
  - Persists the voice interaction to the real audit trail (actor `voice_agent`) so promise/dispute capture survives a refresh and shows up in `GET /api/audit/`.
