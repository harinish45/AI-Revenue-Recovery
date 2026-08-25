# RecoverAI API Contract

Base URL: http://localhost:8000

## Canonical endpoints

- POST /api/demo/seed
- POST /api/demo/reset
- GET /api/dashboard/summary
- GET /api/cases
- GET /api/cases/{case_id}
- POST /api/execution/execute with {"case_id":"RC-..."} and an Idempotency-Key
- GET /api/audit
- GET /api/audit/{audit_id}/verify
- POST /api/demo/recovery-batch
- POST /api/demo/simulate-failure
- POST /api/cases/{case_id}/voice-events
- POST /api/webhooks/razorpay

Execution is policy-gated and never authorizes money movement by itself.
Webhooks validate an optional HMAC secret, append an audit event, and return an
enqueue acknowledgement; a production worker is the next integration boundary.

## Compatibility

/api/recovery/* and /api/batch/process remain deprecated aliases for older
hackathon clients. New clients must use the canonical paths above.
