<div align="center">

# 🤖 RecoverAI — Autonomous Revenue Recovery Agent

**The AI agent that recovers failed payments — without ever moving money on its own.**

`Detect → Diagnose → Decide → Recover → Audit`

![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Razorpay](https://img.shields.io/badge/Razorpay-Integrated-0C2451?logo=razorpay&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-67%20passing-brightgreen)
![License](https://img.shields.io/badge/License-MIT-blue)

[![Backend CI](https://github.com/harinish45/AI-Revenue-Recovery/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/harinish45/AI-Revenue-Recovery/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/harinish45/AI-Revenue-Recovery/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/harinish45/AI-Revenue-Recovery/actions/workflows/frontend-ci.yml)
[![Secret Scan](https://github.com/harinish45/AI-Revenue-Recovery/actions/workflows/secret-scan.yml/badge.svg)](https://github.com/harinish45/AI-Revenue-Recovery/actions/workflows/secret-scan.yml)

*RecoverAI does not let the model move money. The model recommends; deterministic policy decides; the provider confirms; only confirmed payment events count as recovered revenue; every decision is auditable and every unsafe path escalates.*

</div>

---

## 🎥 Demo

<video src="https://github.com/harinish45/AI-Revenue-Recovery/raw/main/video/RecoverAI-Demo.mp4" controls width="100%"></video>

**Best experience:** open the [live Render demo](https://recoverai-5orn.onrender.com)
in **Microsoft Edge** — it ships the strongest built-in neural voices for the
multilingual Smart Collect voice agent, and everything else in the video runs
identically there, live, in Razorpay Test Mode.

If the player above doesn't load, [download/watch the video directly](video/RecoverAI-Demo.mp4).

---

### Contents

[Demo](#-demo) · [The Problem](#-the-problem) · [Quickstart (any OS)](#-quickstart) · [The Solution](#-the-solution) · [Architecture](#️-architecture) · [Project Structure](#-project-structure) · [API Highlights](#-api-highlights) · [End-to-End Workflow](#-real-end-to-end-workflow) · [Operator Cockpit](#️-operator-cockpit) · [Test Matrix](#-adversarial-test-matrix) · [Security Layers](#️-security-posture--defense-in-depth) · [Design Decisions](#-design-decisions--trade-offs) · [Roadmap](#️-roadmap)

---

## 💡 The Problem

Indian digital merchants lose **billions of rupees every year** to failed payments — UPI declines, gateway timeouts, insufficient balances, abandoned checkouts. Most of that money is *recoverable*, but recovery requires judgment: *why* did the payment fail, *who* should be contacted, *how*, and — critically — *when not to*.

Human ops teams can't scale to thousands of daily failures. Naive automation retries blindly, spams customers, breaches compliance, and double-charges.

## 🚀 Quickstart

**Live demo:** [recoverai-5orn.onrender.com](https://recoverai-5orn.onrender.com)

**Paste one line into a terminal.** It clones the repo (if you don't already
have it) and starts the whole app — nothing else to install first except
Docker. Same result on Windows, macOS, and Linux.

**macOS / Linux (Terminal):**

```bash
curl -fsSL https://raw.githubusercontent.com/harinish45/AI-Revenue-Recovery/main/bootstrap.sh | bash
```

**Windows (PowerShell):**

```powershell
irm https://raw.githubusercontent.com/harinish45/AI-Revenue-Recovery/main/bootstrap.ps1 | iex
```

### 👉 Open **http://localhost:8000**

That's the whole cockpit — standalone dashboard, voice agent, everything. (The
React dev dashboard, if you want it separately, is on http://localhost:5173.)
Both containers run as a non-root user with a `HEALTHCHECK` — see
[Security Posture](#️-security-posture--defense-in-depth). Stop it any time
with `docker compose down` from inside the cloned folder.

Already have the repo cloned? Skip the line above and just run
`docker compose up --build` from inside it — same result. Verified end to end
against a genuinely fresh clone with zero local config: builds, starts, and
`/api/demo/seed` works immediately, no `.env` file required.

<details>
<summary><strong>Prefer running it without Docker?</strong></summary>

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env            # Razorpay test keys optional — simulation is on by default
uvicorn app.main:app --reload
```

Open **http://localhost:8000**. To also run the React dev dashboard
separately: `cd frontend && npm install && npm run dev` → http://localhost:5173.

Local demo controls (seed / reset / batch / failure simulation) need one more
line in `backend/.env`:

```bash
DEMO_MODE=true
```

</details>

### Voice agent: use Microsoft Edge

The voice agent is a real browser interaction: it requests microphone input,
recognizes speech, speaks replies aloud, and records consent and outcomes to
the backend audit trail. Payments remain simulated in this test-mode demo;
the voice conversation and audit events are real.

For the best result, open either the [live Render demo](https://recoverai-5orn.onrender.com)
or `http://localhost:8000` in **Microsoft Edge**. Edge generally provides the
best built-in neural voices for the supported Indian languages. Allow the
microphone permission when prompted, select a case, check the consent box,
and start the call. If a language voice is missing, the agent intentionally
shows the response as text instead of playing incorrect pronunciation.

The live Render URL uses HTTPS, so microphone access is supported. When using
the React development dashboard separately, run it at `http://localhost:5173`
and keep the backend running at `http://localhost:8000`.

Render and localhost use the same standalone cockpit and backend API. If Edge
reports that a language voice is unavailable, install that language's speech
pack in Windows **Settings → Time & language → Language & region**, restart
Edge, and reload the page. Speech recognition retries the language's primary
tag automatically when a regional tag is rejected; typed replies remain
available as a safe fallback.

### Run the test suite

```bash
cd backend && python -m pytest tests/ -v      # 67 tests: safety, adversarial, business logic, API
```

## ✨ The Solution

RecoverAI is a **bounded autonomous agent** that turns failed payments into a governed recovery pipeline:

| Stage | What happens | Guardrail |
|---|---|---|
| 🔍 **Detect** | Failed payments become tracked recovery cases | Amounts reconciled between payment & case |
| 🧠 **Diagnose** | AI classifies the failure root cause with evidence + confidence | Model output can never override deterministic classification |
| ⚖️ **Decide** | 11-check deterministic policy engine approves or blocks | The agent *recommends*; policy *decides* |
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
│  │ (bounded) │  │ (11 gate) │  │ (provider) │  │ (SHA-256)  │  │
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
- **Multilingual voice cockpit** — the voice-recovery playbook negotiates promise-to-pay across 8 Indian languages, each spoken and recognized in its own native script (no English mixed into a non-English reply), with every promise gated behind explicit recorded consent. It also recognizes disputes ("I already paid this") as a distinct, audited outcome from a refusal — never silently retried — and is honest when a device has no matching voice installed: it shows text instead of playing mispronounced audio through a mismatched language engine.
- **Evidence-weighted confidence, not a lookup table** — the agent's confidence score is a function of the customer's actual payment history (success rate, prior failures, history depth), not a fixed number per failure category. Two customers with the same failure reason and different track records get different confidence — and that number is what the policy engine's 0.70 gate actually reads.

## 📁 Project Structure

```text
backend/
├── app/
│   ├── routers/         cases · execution · webhooks · audit · demo · batch
│   ├── services/         recovery_executor · payment_confirmation · batch_executor
│   │                      policy_engine · decision_engine · diagnosis_service
│   │                      audit_service · razorpay_service · metrics_service
│   ├── security/          API-key auth boundary
│   └── models.py · schemas.py · main.py
├── migrations/          Alembic migrations (real, verified up/down against a
│                          clean database — see Design Decisions)
└── tests/                67 tests — safety, adversarial, business logic, API

frontend/src/
├── components/         CasesTable · CaseDetailModal · AuditDrawer
│                        BatchResultModal · MetricsRow · TopBar · ArchFlow …
├── hooks/               useDashboardData · useCaseExecution · useBatchRecovery
│                         useAuditTrail · useNotices · useShortcuts · useClipboard
├── api.js · constants.js · utils/
└── main.jsx             thin composition root — no business logic

RecoverAI-standalone.html   zero-build, single-file cockpit — the full feature
                            set (voice agent, playbooks, promises, settings) —
                            plus the same case/execution/audit core as above
```

Routers stay thin, services own the logic, the policy engine is the single
gate every execution passes through, and the React app is decomposed into
single-purpose hooks and components rather than one monolithic file —
structured the way a codebase meant to be extended, not just demoed, should be.

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
| `POST` | `/api/cases/{id}/voice-events` | Voice promises, disputes, and call outcomes across 8 languages — a promise is rejected without explicit consent |
| `POST` | `/api/demo/*` | Seed · reset · batch · failure simulation (dev-only, token-gated) |

## 🔄 Real End-to-End Workflow

Not a mockup — this is an actual `curl` session against a running instance, captured verbatim. Six calls, five pipeline stages, one tamper-evident chain.

```bash
# 1. Detect — seed synthetic failed payments into tracked recovery cases
$ curl -X POST localhost:8000/api/demo/seed
{"created_records":100,"message":"Demo dataset seeded with 100 payments and 25 recovery cases."}

# 2. Diagnose — the agent already classified root cause + recommended action
$ curl localhost:8000/api/cases?limit=1
{"id":"RC-IL_002","customer_name":"Deepika Rao","amount":23565.27,
 "failure_category":"temporary_gateway_failure","recommended_action":"retry_payment", ...}

# 3. Decide + Recover — policy gate runs, then the approved action executes
$ curl -X POST localhost:8000/api/execution/execute \
       -H "Idempotency-Key: demo-1" -d '{"case_id":"RC-IL_002"}'
{"case_id":"RC-IL_002","status":"recovered","recovered_amount":23565.27,
 "message":"Recovery succeeded (Simulated).","audit_event_id":"AUD-85CD6C9B"}

# 4. Audit — every stage left its own sealed, hash-chained event
$ curl localhost:8000/api/audit?case_id=RC-IL_002
{"items":[
  {"event_type":"recovery_succeeded",   "sequence":4, "event_hash":"c1ec7e…20e33"},
  {"event_type":"razorpay_simulation",  "sequence":3, "event_hash":"b409b0…02b59"},
  {"event_type":"analysis_completed",   "sequence":2, "event_hash":"9e8d80…86451d"},
  {"event_type":"payment_failure_detected", "sequence":1, "event_hash":"5bdfbe…d8d9ed0"}
], "total":4}

# 5. Verify — recompute every hash in the chain from the root forward
$ curl localhost:8000/api/audit/chain/verify
{"valid":true,"events_checked":52, "events":[
  {"audit_id":"AUD-B43D65F5","sequence":1,"valid":true,"hash_ok":true,"chain_link_ok":true},
  {"audit_id":"AUD-85CD6C9B","sequence":4,"valid":true,"hash_ok":true,"chain_link_ok":true},
  ...
]}

# 6. Replay the same idempotency key — no double execution, no double-count revenue
$ curl -X POST localhost:8000/api/execution/execute \
       -H "Idempotency-Key: demo-1" -d '{"case_id":"RC-IL_002"}'
{"case_id":"RC-IL_002","status":"recovered", ...}   # identical response, not re-run
```

Each hash embeds the previous event's hash (`previous_hash` → next `event_hash`), so
step 5 isn't a status flag — it's a real chain walk, recomputing every link from the
root, that fails loudly the moment one byte of history is altered. Reproduce it
yourself: run any Quickstart option above, then `POST /api/demo/seed` and follow the
six calls.

## 🎛️ Operator Cockpit

`RecoverAI-standalone.html` (what's actually live at the deployed URL) went
through a real usability and honesty pass, not just a features pass:

- **Webhooks that actually work, not a fake outbound-registration form.** The
  Settings → Webhooks tab used to let you "add" destination URLs saved only
  to `localStorage` — the backend never saw them, and RecoverAI *receives*
  Razorpay events, it doesn't send them. It now shows the real inbound
  webhook URL to paste into your Razorpay Dashboard, explains
  `WEBHOOK_SECRET`, and has a **Send a test webhook** button that POSTs an
  accurately-shaped Razorpay `payment.captured` / `payment_link.paid` /
  `payment.failed` / `refund.processed` payload straight to
  `/api/webhooks/razorpay` — the real endpoint — and shows the real response.
  Sending a confirming event for a case that's `awaiting_payment` flips it to
  `recovered`, live, in the same tab.
- **Settings, reorganized.** It was two stacked, overlapping tab bars mixing
  voice preferences, a chaos-testing "Failure Simulation" toggle, destructive
  Seed/Reset buttons with no confirmation, and two near-duplicate readiness
  checklists that disagreed with each other (one still listed signed
  webhooks as "NEXT" after the backend already implemented them). Now 7
  flat, single-purpose tabs — General, Developer Tools, Data, Readiness,
  Integration, Webhooks, Account — one readiness checklist, and a real
  confirmation prompt before Reset All deletes anything.
- **Playbooks got their own page.** Clicking a playbook used to run it
  immediately with no way to see what it was about to touch. Each of the 9
  playbooks (3 new: Low-Risk Auto-Retry, Small-Ticket Batch Clear, Second
  Attempt Ladder) now opens a detail page listing exactly which live cases
  are eligible before you run it.
- **Payment Pages and Route stopped being the same page with different
  copy.** Payment Pages now shows real payment-link case data (sent /
  awaiting / paid, and the actual cases); Route shows a live breakdown of
  every case by the policy engine's actual routed action.
- **Smart Collect (voice) navigation.** The voice cockpit is now a
  three-step flow — choose a case, set up the call, run it — with a
  persistent step bar and a single, always-visible way back, instead of one
  easy-to-miss link. The pre-call screen is a proper two-column form (case
  facts alongside language, consent, and start) instead of a centered
  stack of empty space, and the live-call console is height-bounded to the
  viewport so the reply controls never require scrolling to reach.
- **The Execute button couldn't tell an already-`awaiting_payment` or
  `closed` case from an actionable one, in both frontends.** Each kept its
  own copy of which statuses count as terminal, and both copies had gone
  stale relative to the backend's real list — missing `awaiting_payment`
  and `closed` (added this session for completed voice calls). Clicking
  Execute on one of those cases still round-tripped to the backend, which
  correctly rejects it, but for `awaiting_payment` specifically the
  rejection response still carries `status: "awaiting_payment"`, which the
  React app's status branching misread as "intervention just sent" — a
  false success message for a click that changed nothing. Fixed in both:
  the standalone cockpit now calls its one canonical `isTerminalCase()`
  helper everywhere instead of four separate hardcoded copies of the list;
  the React app's `TERMINAL_STATES` constant now matches the backend's
  exactly.

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
- ✅ Voice events accept full BCP-47 tags (`hi-IN`, `mr-IN`, …) across all 8 supported languages
- ✅ Transcripts, intents, languages, confidence values are schema-bounded
- ✅ Demo control plane is disabled in production mode

The voice cockpit itself has its own browser-side regression suite (jsdom, run
against the real page — not mocked-out logic): a fast double-submit can't
create two agent replies for one customer turn; every agent line across all
7 non-English languages is scanned for stray Latin words (0 leaks); a
dropped/stuck TTS utterance recovers instead of freezing the call; a
customer disputing a charge produces a real `voice_dispute_raised` event,
not a generic refusal; and a sentence that never literally appears in the
pattern list ("I really don't have the money to pay right now") still
correctly resolves to the right intent instead of falling to the generic
fallback, because scoring gives partial credit for significant word overlap,
not just exact phrase matches.

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
Policy checks:         11/11 passed
Audit seal:            AUD-88f2…c1a9   (chain verified)
```

## 🛡️ Security Posture — Defense in Depth

Every request crosses eight independent layers before it can touch money or the audit
record. No single layer is trusted alone — a bypass of one still hits the next.

```text
 L1  Transport & headers    CSP · Permissions-Policy · HSTS · COOP · CORP ·
        │                   X-Frame-Options · X-Content-Type-Options — set on every
        │                   response, not just claimed in a doc
 L2  Request size ceiling   rejected from Content-Length alone, before the body is
        │                   even read — bounds every route, not only webhooks
 L3  Authentication         X-API-Key · readonly/operator roles · refuses to boot in
        │                   production without API_KEYS, AUDIT_SIGNING_KEY, AND
        │                   WEBHOOK_SECRET all configured (a prod deploy that left
        │                   RAZORPAY_SIMULATE=true used to boot fine with an
        │                   unconfigured webhook secret and silently accept
        │                   unauthenticated "payment confirmed" events — closed)
 L4  Input validation       Pydantic schemas — language allowlists, transcript/intent
        │                   bounds, confidence range, pagination ceilings; case search
        │                   escapes SQL LIKE wildcards so a literal '%'/'_' in a
        │                   customer name can't silently broaden a match
 L5  Rate limiting          per-endpoint throttling on execute, demo, voice routes —
        │                   uvicorn now runs with --proxy-headers/--forwarded-allow-ips
        │                   so the limiter keys on the real client IP behind Render's
        │                   load balancer, not the LB's own IP for every request
 L6  Business policy gate   the 11-check safety contract (see above) — the one place
        │                   that decides whether an intervention is allowed to run
 L7  Idempotency ledger     Idempotency-Key request-hash separation; replay returns
        │                   the original result, cross-case reuse returns 409 — backed
        │                   by row-level locking (see Concurrency Safety below), not
        │                   just the idempotency table alone
 L8  Tamper-evident audit   HMAC-SHA256-sealed, hash-chained event log — forging a
                            self-consistent chain needs AUDIT_SIGNING_KEY, not just DB
                            access — plus a chain-tail anchor (see below) that catches
                            deletion of the *newest* event, which pure hash-linking
                            alone structurally cannot detect
```

### Concurrency safety — closing the double-execution race

Every case-mutating endpoint (`execute`, `confirm-payment`, the Razorpay webhook
handler, batch recovery, voice events) re-fetches its case row under
`with_for_update()` as the first thing it does — a real row lock on Postgres in
production, a documented no-op on SQLite. Without this, two concurrent requests for
the same case (a UI double-click, a client retry that reused a *different*
Idempotency-Key, or a webhook racing an operator's manual confirmation) could both
read `pending`/`awaiting_payment`, both pass the policy gate, and both call the
payment provider before either commit was visible to the other — a real
double-send / double-counted-revenue risk that only surfaces under production
concurrency, never in a single-request demo. The lock makes the second request
block until the first commits, so it then sees the now-terminal status and the
policy engine's own `terminal_state_check` correctly blocks it — no new bypass
logic needed, the existing safety contract just gets to actually run. Batch
recovery re-locks each case individually with `skip_locked=True` right before
processing it, so two overlapping batch triggers split the work across disjoint
cases instead of blocking on or double-processing the same one.

### Audit-chain tamper detection, made actually complete

`verify_chain()`'s hash-linking only ever points *backward* — each seal embeds the
previous seal's hash. That means deleting the single newest `AuditLog`/`AuditSeal`
row pair for a case leaves every *remaining* seal perfectly self-consistent, and a
forward-only walk reports the truncated chain as 100% valid. Every sealed event now
also writes `last_audit_sequence`/`last_audit_hash` onto the case row itself, in the
same transaction as the seal — an anchor stored outside the seals table entirely, so
deleting seal/log rows alone can't erase it. `verify_chain()` cross-checks this
anchor against what it can still find and reports a mismatch (`anchor_mismatches`)
as truncation. A `UNIQUE(case_id, sequence)` constraint on `audit_seals` backs this
up as defense in depth. The audit drawer in the React dashboard has a "Verify full
chain" action that calls this end to end and surfaces the result — not just
per-event seal checks.

Plus, orthogonal to the request path:

- **Webhook integrity, verified against the real shape** — HMAC-SHA256 signature verification (timing-safe compare), replay dedup via the real `X-Razorpay-Event-Id` header (not a body field that real Razorpay deliveries don't send), a staleness window read from the real `created_at` field, event-type allowlist, payload size cap. Payment confirmation reads `payload.payment.entity.id` — the actual Razorpay nesting — not a shallower shape that would silently never match. A test proves an accurately-shaped `payment_link.paid` delivery flips a real case to `recovered` end to end.
- **CI security scanning on every push** — `pip-audit` + `npm audit` (dependency CVEs), `bandit` (Python SAST), Gitleaks (secret scanning), Dependabot (pip/npm/Actions/Docker); frontend CI now also runs `eslint` as a real lint gate (there wasn't one before)
- **Reproducible builds** — frontend dependencies (`react`, `vite`, `@vitejs/plugin-react`, `typescript`) were pinned to `"latest"`, meaning every fresh `npm install` could silently pull a different, untested version; all now pinned to the exact versions this repo is built and tested against
- **Container hardening** — both images run as a non-root user with a `HEALTHCHECK`; base images and CI Actions kept current (Python 3.14, Node 26, nginx 1.31, `actions/checkout@v7`, `actions/setup-python@v7`, `actions/setup-node@v7`, `gitleaks-action@v3`) — each bump verified before applying, not merged blindly (see commit history for how)
- **Demo isolation** — `/api/demo/*` triple-guarded: off by default, hard-disabled in production, optional shared-token gate
- **Independently reviewed** — this repo's hardening work has been through a dedicated multi-pass security review (vulnerability identification against the actual diff, followed by independent false-positive filtering of every candidate finding) with no reportable high-confidence issues found

See [`docs/security.md`](docs/security.md) for the full control list and threat model.

## 🎯 Design Decisions & Trade-offs

Every choice below was deliberate, not a shortcut we ran out of time to fix. Each
one trades a capability for a safety or reproducibility guarantee — read this
before concluding any of them is a gap.

**Why the agent is deterministic-first, with the model as an optional layer, not the core.**
`services/recovery_agent.py` classifies and scores confidence from real evidence
(the customer's actual payment history) without calling any external model —
that path is what runs by default, and it's what makes every decision in this
README reproducible on demand. An LLM-assisted suggestion path already exists
(`AI_DIAGNOSIS_ENABLED` + `OPENAI_API_KEY`, see `services/diagnosis_service.py`)
and can propose an action — but it still can't move money, because the policy
engine has veto power over the model's output too, same as the deterministic
path. The model was kept optional specifically so this system's core safety
property — "the policy engine decides, not the model" — holds regardless of
whether a model is even configured. That's the harder, more defensible design;
a model call wrapped in a `try/except` is not what makes an agent trustworthy.

**Why every payment action is simulated, never live.**
This repo has never sent a real rupee anywhere, on purpose. The architecture is
provider-agnostic by construction (`services/razorpay_service.py` is the only
file that would change to add a real credential path — everything upstream of
it, including the entire policy gate and audit chain, is provider-independent
already). Wiring in live payment credentials for a hackathon demo is the
irresponsible option, not the missing one — it would mean testing money-moving
code against strangers' cards with no operational safety net. The correct
sequence is: prove the safety architecture first (this repo), then connect a
real provider behind it (see Roadmap) — not the reverse.

**Why voice uses the browser's built-in speech APIs instead of a paid cloud service.**
This keeps the demo running with zero API keys, zero signup, and zero recurring
cost for anyone who clones it. The trade-off is real: pronunciation quality
depends on what voices the browser/OS already has installed (Microsoft Edge
ships strong neural voices for all 8 languages out of the box; Chrome often
doesn't). Rather than hide that, the app is honest about it at runtime — see
`voiceDiagnostics()` and the in-call fallback notice in
`RecoverAI-standalone.html` — and shows text instead of playing mispronounced
audio through the wrong engine. A production deployment would swap in a paid
TTS/STT provider behind the same `speakText()`/`startListening()` interface;
nothing else in the conversation logic would need to change.

**Why there are two frontends, and why they're not identical.**
`RecoverAI-standalone.html` is the full-featured reference cockpit — cases,
execution, audit, batch, *and* the multilingual voice agent, playbooks, and
promise tracking — in one file with zero build step, so anyone reviewing this
without Node installed can open it and see the complete product in ten
seconds. `frontend/src/` (React) is a lighter, actively-developed operational
dashboard covering the core case/execution/audit loop; it's the surface for
day-to-day recovery work, not a mirror of every cockpit feature. They share
the same backend API contract for everything both of them implement — that
part is real, testable overlap, not a claim — but "byte-for-byte parity"
would be the wrong way to describe two apps with deliberately different
scope, so this README doesn't say that anymore.

**Why SQLite, not Postgres, right now.** Zero setup, zero external dependency,
same SQLAlchemy models either way — `DATABASE_URL` is genuinely the only thing
that changes to point this at Postgres in production: real Alembic migrations
already exist (`backend/migrations/`, verified upgrade *and* downgrade against
a clean database), and `create_engine`'s connection args are resolved per-
dialect rather than hardcoding a SQLite-only argument that would otherwise
crash a Postgres connection at startup. Shipping a demo that requires standing
up a database server before a reviewer can even run it would trade real
accessibility for a production property nobody evaluating a submission
actually needs yet — but the migration path off SQLite is real code today,
not a promise.

## 🗺️ Roadmap

- [x] Alembic migrations (see `backend/migrations/`; SQLite retained deliberately for zero-setup demos — swap `DATABASE_URL` to a Postgres URL and the same migration runs unchanged)
- [ ] Redis-backed distributed rate limiting & batch queue
- [ ] SSE batch progress with real per-case status streaming
- [ ] PII masking layer with role-based field visibility
- [ ] LLM-backed diagnosis with response-hash provenance (currently deterministic + heuristic AI)

## 📄 License

MIT — see [LICENSE](LICENSE).

<div align="center">
<sub>Built for the Razorpay Buildathon · RecoverAI — the agent that earns the right to act, every single time.</sub>
</div>
