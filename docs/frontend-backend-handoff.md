# RecoverAI Frontend/Backend Handoff

## Ownership

- Frontend: ChatGPT → `frontend-dev`
- Backend: Qwen → backend work

## Current frontend baseline

The frontend branch contains:

- Vite + React entrypoint
- RecoverAI dashboard shell
- Revenue metrics cards
- Recovery queue
- Agent decision panel
- Audit activity panel
- Responsive design system
- API client in `frontend/src/api.js`
- `VITE_API_BASE` environment variable

## Backend integration target

Implement the endpoints in `docs/api-contract.md` exactly, especially:

- `GET /dashboard/summary`
- `GET /recovery/cases`
- `GET /recovery/cases/{id}`
- `POST /recovery/cases/{id}/execute`
- `GET /recovery/audit`
- `POST /demo/seed`
- `POST /demo/reset`
- `POST /demo/recovery-batch`
- `POST /demo/simulate-failure`

## Integration rules

1. Keep response field names stable.
2. Keep money values numeric in JSON; frontend formats INR.
3. Return timestamps as ISO 8601 strings.
4. Use the documented error object for non-2xx responses.
5. Enforce recovery policies on the backend; frontend controls are not authorization.
6. Never commit Razorpay secrets.

## Demo requirements

The backend should provide deterministic demo data so the frontend can reliably show:

- Revenue at risk
- Successful recovery
- Failed recovery
- Escalation
- Audit events

The frontend should be able to run the entire pitch flow from a clean local start.
