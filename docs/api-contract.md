# RecoverAI API Contract

Base URL: `/api`

All responses are JSON. Financial actions are server-side gated. The frontend never performs payment actions directly.

## GET /dashboard/summary
Returns aggregate metrics for the current demo/merchant dataset.

```json
{
  "total_transactions": 100,
  "total_revenue": 124500,
  "failed_payments": 20,
  "revenue_at_risk": 18750,
  "recovered_amount": 7250,
  "recovery_rate": 38.7,
  "recovery_attempts": 15,
  "successful_recoveries": 9,
  "failed_recoveries": 6,
  "escalated_cases": 3
}
```

## GET /recovery/cases
Optional query parameters: `status`, `risk`, `page`, `page_size`, `search`.

```json
{
  "items": [
    {
      "id": "RC-001",
      "customer": {"id":"CUS-001","name":"Arjun Kumar","email":"demo@example.com"},
      "payment_id": "pay_demo_001",
      "amount": 2499,
      "currency": "INR",
      "failure_reason": "Gateway timeout",
      "risk_level": "HIGH",
      "recommended_action": "RETRY_PAYMENT",
      "status": "READY",
      "retry_count": 0,
      "max_retries": 2,
      "recovered_amount": 0,
      "created_at": "2026-08-22T18:01:02Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 25
}
```

## GET /recovery/cases/{id}
Returns the full recovery case, customer history, agent decision, policy checks and audit events.

## POST /recovery/cases/{id}/execute
Executes the backend-approved recovery action. The backend enforces retry/amount/idempotency policies.

Success:
```json
{
  "case_id": "RC-001",
  "status": "RECOVERED",
  "recovered_amount": 2499,
  "action": "RETRY_PAYMENT",
  "message": "Recovery succeeded in Razorpay Test Mode."
}
```

Failure:
```json
{
  "case_id": "RC-001",
  "status": "FAILED",
  "recovered_amount": 0,
  "action": "RETRY_PAYMENT",
  "message": "Test gateway failure.",
  "escalated": true
}
```

## GET /recovery/audit
Optional query parameters: `case_id`, `page`, `page_size`.

```json
{
  "items": [
    {
      "id": "AUD-001",
      "case_id": "RC-001",
      "event_type": "RECOVERY_SUCCEEDED",
      "actor": "recovery_executor",
      "decision": "RETRY_PAYMENT",
      "reason": "Eligible customer below retry limit",
      "action": "RETRY_PAYMENT",
      "result": "SUCCESS",
      "timestamp": "2026-08-22T18:01:05Z"
    }
  ],
  "total": 1
}
```

## POST /demo/seed
Seeds deterministic synthetic data. Returns updated summary.

## POST /demo/reset
Resets the demo dataset to its initial state.

## POST /demo/recovery-batch
Runs the bounded recovery workflow over the eligible batch. Returns aggregate results and updated metrics.

## POST /demo/simulate-failure
Creates/executes a deterministic failure scenario. It must stop safely, log an audit event and return the case status.

## Error contract
HTTP 4xx/5xx:
```json
{
  "error": {
    "code": "POLICY_BLOCKED",
    "message": "Maximum retry limit reached.",
    "details": {}
  }
}
```

The frontend must display `error.message` and must never retry financial actions automatically.

## Integration rules
- Test Mode only.
- Secrets remain backend-only.
- Frontend never calls Razorpay directly.
- Backend must preserve response field names once integration begins.
- Breaking contract changes require updating this document before frontend/backend changes are merged.
