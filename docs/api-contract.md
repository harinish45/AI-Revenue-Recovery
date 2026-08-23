# RecoverAI API Contract (Final Integration Update)

In addition to the `/api/recovery/*` routes, the backend explicitly exposes the following root-level routes to guarantee frontend compatibility:

## GET /api/cases/
Equivalent to `/api/recovery/cases`.

## GET /api/cases/{id}
Equivalent to `/api/recovery/cases/{id}`.

## POST /api/execution/execute
Executes recovery using a JSON body.
Request:
```json
{
  "case_id": "RC-..."
}
```
Response: Same as `ExecuteResponse`.

## GET /api/audit/
Equivalent to `/api/recovery/audit`.

## POST /api/batch/process
Equivalent to `/api/demo/recovery-batch`. Returns batch metrics:
```json
{
  "total_cases": 20,
  "attempted": 15,
  "successful": 9,
  "failed": 4,
  "escalated": 2,
  "amount_at_risk": 18750.0,
  "amount_recovered": 7250.0,
  "recovery_rate": 38.67
}
```
