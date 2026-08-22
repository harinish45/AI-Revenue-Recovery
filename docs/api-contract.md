# RecoverAI API Contract v1

Base URL: `http://localhost:8000/api`

JSON requests/responses unless otherwise noted.

## GET /dashboard/summary
Returns aggregate metrics calculated from backend data.

Response:
```json
{
  "total_revenue": 124500,
  "revenue_at_risk": 18750,
  "recovered_amount": 7250,
  "recovery_rate": 38.7,
  "total_transactions": 100,
  "failed_payments": 20,
  "recovery_attempts": 15,
  "successful_recoveries": 9,
  "failed_recoveries": 6,
  "escalated_cases": 3
}
```

## GET /recovery/cases
Optional query params: `status`, `risk_level`, `search`, `page`, `limit`.

Response:
```json
{
  "items": [
    {
      "id": "RC-001",
      "payment_id": "pay_demo_001",
      "customer_id": "cus_001",
      "customer_name": "Arjun Kumar",
      "amount": 2499,
      "currency": "INR",
      "failure_category": "temporary_gateway_failure",
      "failure_reason": "Gateway timeout",
      "risk_level": "high",
      "recommended_action": "retry_payment",
      "action_status": "eligible",
      "recovery_status": "pending",
      "recovered_amount": 0,
      "retry_count": 0,
      "created_at": "2026-08-22T18:00:00Z"
    }
  ],
  "page": 1,
  "limit": 20,
  "total": 1
}
```

## GET /recovery/cases/{id}
Returns case details, customer/payment context, decision explanation, policy checks, and audit events.

## POST /recovery/cases/{id}/execute
Executes the bounded recovery action selected by the backend policy engine.

Response:
```json
{
  "case_id": "RC-001",
  "status": "recovered",
  "recovered_amount": 2499,
  "message": "Recovery succeeded in Razorpay Test Mode.",
  "audit_event_id": "AUD-001"
}
```

Possible status values: `recovered`, `failed`, `needs_human_review`, `blocked`.

## GET /recovery/audit
Optional query params: `case_id`, `page`, `limit`.

Response:
```json
{
  "items": [
    {
      "id": "AUD-001",
      "case_id": "RC-001",
      "event_type": "recovery_executed",
      "actor": "recoverai-agent",
      "decision": "retry_payment",
      "reason": "Customer has successful payment history and retry limit is not reached.",
      "action": "retry_payment",
      "result": "success",
      "timestamp": "2026-08-22T18:01:00Z"
    }
  ],
  "page": 1,
  "limit": 50,
  "total": 1
}
```

## POST /demo/seed
Creates deterministic synthetic demo data. No request body required.

Response:
```json
{
  "created_records": 100,
  "message": "Demo dataset seeded."
}
```

## POST /demo/reset
Resets the demo dataset.

## POST /demo/recovery-batch
Processes eligible recovery cases using backend policy rules.

Response:
```json
{
  "processed": 20,
  "successful": 9,
  "failed": 6,
  "escalated": 3,
  "recovered_amount": 7250
}
```

## POST /demo/simulate-failure
Creates or triggers one deterministic recovery failure for the pitch demo.

Response:
```json
{
  "case_id": "RC-FAIL-001",
  "status": "failed",
  "message": "Simulated gateway failure handled gracefully."
}
```

## Error format

All non-2xx responses should use:
```json
{
  "error": {
    "code": "RECOVERY_EXECUTION_FAILED",
    "message": "Human-readable explanation.",
    "request_id": "req_123"
  }
}
```

Critical financial policy enforcement is backend-only. The frontend must never assume that a recovery is allowed merely because a button is visible.
