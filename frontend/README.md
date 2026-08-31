# RecoverAI Frontend

React/Vite merchant dashboard for the AI Revenue Recovery hackathon project.

## Run

```bash
cd frontend
npm install
npm run dev
```

Optional backend URL:

```bash
VITE_API_BASE=http://localhost:8000/api
```

Copy `.env.example` to `.env` locally. Never commit secrets.

## Backend integration

The frontend uses `src/api.js` and the shared contract at `docs/api-contract.md`.

When the backend is unavailable, the dashboard intentionally falls back to deterministic demo data so the UI remains usable for a walkthrough. It never claims those demo values are live Razorpay transactions.

## Main flows

- Overview metrics
- Recovery queue and search
- Recovery case detail modal
- Bounded recovery execution
- Batch execution
- Audit trail
- Policy guardrails
- Reset/seed/demo controls
- Graceful backend/API errors
