<div align="center">

# 🤖 RecoverAI — Autonomous Revenue Recovery Agent

**The AI agent that recovers failed payments — without ever moving money on its own.**

`Detect → Diagnose → Decide → Recover → Audit`

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![Razorpay](https://img.shields.io/badge/Razorpay-Integrated-0C2451?logo=razorpay&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-40%20passing-brightgreen)
![License](https://img.shields.io/badge/License-MIT-blue)

*RecoverAI does not let the model move money. The model recommends; deterministic policy decides; the provider confirms; only confirmed payment events count as recovered revenue; every decision is auditable and every unsafe path escalates.*

</div>

---

## 💡 The Problem

Indian digital merchants lose **billions of rupees every year** to failed payments — UPI declines, gateway timeouts, insufficient balances, abandoned checkouts. Most of that money is *recoverable*, but recovery requires judgment: *why* did the payment fail, *who* should be contacted, *how*, and — critically — *when not to*.

Human ops teams can't scale to thousands of daily failures. Naive automation retries blindly, spams customers, breaches compliance, and double-charges.

## ✨ The Solution

RecoverAI is a **bounded autonomous agent** that turns failed payments into a governed recovery pipeline:

| Stage | What happens | Guardrail |
|---|---|---|
| 🔍 **Detect** | Failed payments become tracked recovery cases | Amounts reconciled between payment & case |
| 🧠 **Diagnose** | AI classifies the failure root cause with evidence + confidence | Model output can never override deterministic classification |
| ⚖️ **Decide** | 10-check deterministic policy engine approves or blocks | The agent *recommends*; policy *decides* |
| 💸 **Recover** | Payment link / reminder / retry is executed via Razorpay | A sent link ≠ recovered money — only provider-confirmed events count revenue |
| 🧾 **Audit** | Every step sealed into a SHA-256 tamper-evident chain | Any tampering invalidates the whole chain, verified recursively |

### The Safety Contract

Every execution passes this gauntlet — **in this exact order**:

```text
 1. Load case + payment record      → missing record escalates, never 500s
 2. Economic smart-skip             → intervention cost > recovery value? skip
 3. Eligibility                     → paused/manual_only cases cannot run
 4. Terminal-state protection       → recovered/blocked cases are immutable
 5. Amount ceiling                  → high-value cases always go to humans
 6. Amount reconciliation           → case amount must match payment amount
 7. Retry window                    → cooldowns enforced, not just displayed
 8. Action allowlist                → only whitelisted interventions
 9. Agent confidence ≥ 0.70         → low-confidence AI output never auto-runs
10. Simulated failure injected      → only AFTER policy approval, never before
```

## 🏗️ Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (React + Vite · standalone HTML dashboard)            │
│  Real policy-check visualization · audit chain inspector        │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST (idempotent, rate-limited)
┌──────────────────────────▼──────────────────────────────────────┐
│  FastAPI Backend                                                │
│  ┌───────────┐  ┌───────────┐  ┌────────────┐  ┌────────────┐  │
│  │ Recovery  │→ │ Policy    │→ │ Razorpay   │→ │ Audit      │  │
│  │ Agent     │  │ Engine    │  │ Service    │  │ Chain      │  │
│  │ (bounded) │  │ (10 gate) │  │ (provider) │  │ (SHA-256)  │  │
│  └───────────┘  └───────────┘  └─────┬──────┘  └────────────┘  │
│        │            │                │ signed webhooks          │
│  ┌─────▼────────────▼────────────────▼──────────────────────┐  │
│  │ SQLAlchemy models · idempotency keys · execution ledger  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Key design decisions**

- **Bounded agent** — the AI chooses *which* intervention to recommend with evidence and confidence; a frozen, deterministic policy engine holds veto power over every decision.
- **Honest money lifecycle** — `intervention_sent → awaiting_payment → payment_confirmed → recovered`. Revenue metrics only move on provider confirmation (webhook signature verified, replay-protected, event-allowlisted, size-bounded, timestamp-checked).
- **Idempotent by contract** — `Idempotency-Key` returns the original response on retry; reusing a key for a different case returns `409`.
- **Tamper-evident audit** — per-case monotonic sequence + chained SHA-256 hashes; `/api/audit/chain/verify` re-verifies the entire chain from the root forward.
- **Fail-safe demo isolation** — `/api/demo/*` (seed, reset, simulate-failure) are triple-guarded: `DEMO_MODE=false` by default, hard-disabled when `APP_ENV=production`, optional `X-Demo-Token`.

## 🚀 Quickstart

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env            # Razorpay test keys optional — simulation is on by default
uvicorn app.main:app --reload   # http://localhost:8000/docs
```

Local demo controls (seed / reset / batch / failure simulation) are enabled for development:

```bash
# .env
DEMO_MODE=true
APP_ENV=development
# DEMO_API_TOKEN=optional-shared-secret   → then send X-Demo-Token header
```

### Frontend

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

Prefer zero build tooling? Open **`RecoverAI-standalone.html`** — a self-contained dashboard (the demo surface for judges) with the same API contract.

### Run the test suite

```bash
cd backend
python -m pytest tests/ -v      # 40 tests: safety, adversarial, business logic, API
```

## 🔌 API Highlights

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/dashboard/summary` | Revenue at risk, recovered, open cases, awaiting-payment count |
| `GET` | `/api/cases` | Paginated, filterable recovery cases with policy-check scores |
| `POST` | `/api/execution/execute` | Execute a case (requires `Idempotency-Key`) |
| `POST` | `/api/execution/cases/{id}/confirm-payment` | Provider-confirmed revenue path |
| `POST` | `/api/webhooks/razorpay` | Signature-verified, replay-protected provider events |
| `GET` | `/api/audit/chain/verify` | Recursive tamper-evidence verification |
| `GET` | `/api/audit/{id}/verify` | Verify a single sealed event |
| `POST` | `/api/cases/{id}/voice-events` | Voice promises — rejected without explicit consent |
| `POST` | `/api/demo/*` | Seed · reset · batch · failure simulation (dev-only, token-gated) |

## 🧪 Adversarial Test Matrix

The suite doesn't just test the happy path — it attacks the system:

- ✅ Failure simulation cannot bypass amount limits, terminal states, or max-retries
- ✅ Missing payment record → controlled escalation, never a 500
- ✅ Retry before the cooldown window is rejected
- ✅ `manual_only` / paused cases are blocked
- ✅ Case/payment amount mismatch is rejected
- ✅ Duplicate execution returns the original result (idempotency)
- ✅ Same idempotency key + different case → `409`
- ✅ Successful response returns a verifiable `AUD-…` seal
- ✅ Audit tampering invalidates the complete chain
- ✅ Webhooks: unsigned rejected, stale rejected, unknown event types rejected, missing provider ID rejected, oversized payloads rejected, exact duplicates ignored
- ✅ Voice promise without explicit `consent_confirmed=true` is rejected
- ✅ Transcripts, intents, languages, confidence values are schema-bounded
- ✅ Demo control plane is disabled in production mode

## 📊 Live Economic Intelligence

Every case surfaces the decision math — judges and operators see *why*, not just *what*:

```text
Amount at risk:        ₹1,200
Expected recovery:     91%   (evidence: 2 previous successes, liquidity failure)
Intervention cost:     ₹18
Expected net value:    ₹1,074
Decision:              PAYMENT LINK
Stopping rules:        do not retry the card · escalate after link window
Next permitted retry:  2026-08-28T14:32Z        (24h cooldown)
Policy checks:         10/10 passed   → compliance score 100%
```

## 🛡️ Security Posture

- HMAC-SHA256 webhook signature verification (timing-safe compare)
- Webhook staleness window, event-type allowlist, provider-ID requirement, payload size cap
- Idempotency with request-hash separation and `409` misuse response
- Rate limiting on execute, demo and voice endpoints
- Security headers: CSP, Permissions-Policy, HSTS, COOP, CORP
- Strict Pydantic validation: language allowlists, transcript/intent bounds, confidence range, pagination ceilings
- Demo routes triple-guarded and excluded from production

## 🗺️ Roadmap

- [ ] PostgreSQL + Alembic migrations (SQLite retained deliberately for zero-setup demos)
- [ ] Redis-backed distributed rate limiting & batch queue
- [ ] SSE batch progress with real per-case status streaming
- [ ] PII masking layer with role-based field visibility
- [ ] LLM-backed diagnosis with response-hash provenance (currently deterministic + heuristic AI)

## 📄 License

MIT — see [LICENSE](LICENSE).

<div align="center">
<sub>Built for the Razorpay Buildathon · RecoverAI — the agent that earns the right to act, every single time.</sub>
</div>
