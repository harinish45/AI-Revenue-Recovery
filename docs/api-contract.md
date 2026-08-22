# RecoverAI API Contract

Base URL: `http://localhost:8000/api`

All responses are JSON. Financial actions are server-side gated. The frontend never performs payment actions directly.

## Current backend routes

The backend implementation on `backend-dev` currently exposes these routes:

- `GET /dashboard/summary`
- `GET /cases/?skip=0&limit=100`
- `GET /cases/{case_id}`
- `POST /execution/execute` with `{"case_id": <number>}`
- `GET /audit/?skip=0&limit=100`
- `POST /batch/process`
- Demo routes under `/demo` as implemented by the backend

## GET /dashboard/summary
Returns aggregate metrics for the current dataset.

Expected metrics include total transactions, total revenue, failed payments, revenue at risk, recovered amount and recovery rate.

## GET /cases/
Optional query parameters: `skip`, `limit`.

The current backend returns an array of `RecoveryCase` objects. The frontend adapter accepts either an array or the earlier `{items,total,...}` envelope.

## GET /cases/{id}
Returns one recovery case.

## POST /execution/execute
Request:

```json
{"case_id": 1}
```

The backend must enforce diagnosis, policy checks, retry bounds, duplicate protection and escalation before execution.

## GET /audit/
Optional query parameters: `skip`, `limit`.

Returns audit events ordered newest first.

## POST /batch/process
Runs the backend batch case-generation workflow. The request body follows the backend `BatchProcessRequest` schema.

## Demo

Demo routes are backend-owned. Before final integration, Qwen must document the exact request/response for:

- `POST /demo/seed`
- `POST /demo/reset`
- failure simulation, if implemented

## Frontend normalization

The frontend normalizes:

- `customer_name` → `customer.name`
- `risk_level` → uppercase
- `recommended_action` → uppercase
- `status` / `recovery_status` / `action_status` → `status`
- array responses → `{items: [...]}` internally

## Safety

All financial actions are Test Mode only, bounded by backend policy, and auditable. Frontend validation is never the security boundary.
