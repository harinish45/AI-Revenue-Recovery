# Changelog

All notable changes to RecoverAI, by day. See `git log` for the full commit-level history.

## 2026-08-22 — Initial build
- Bootstrapped repository; scaffolded FastAPI backend (models, routers, services, database) and React/Vite frontend.
- Implemented core recovery API: dashboard, cases, execution, and batch endpoints, backed by a policy engine and audit trail.
- Added Razorpay integration service, synthetic data seeding, and the first backend test suite.
- Established the shared frontend/backend API contract and wired the API client to it.
- Added CI workflows for backend tests and frontend build verification.
- Built out the interactive recovery dashboard: recovery modal, live connection state, batch results, audit drawer, and five-minute pitch demo flow.

## 2026-08-23 — Integration hardening & Razorpay Track 03 completion
- Fixed frontend/backend field mismatches (dashboard fields, status mapping, CORS, API base path).
- Resolved P0/P1 audit issues for an end-to-end deterministic demo.
- Added the LLM provider failover chain, expanded synthetic failure scenarios, and a benchmark script (`scripts/benchmark.py`).
- Visual polish pass: glassmorphism cards, hover micro-animations, risk-level filter pills, responsive breakpoints (1400/768/375px), accessibility improvements.
- Merged parallel frontend/backend development branches into `main`.
- Added one-command local startup scripts (`start.sh`, `start.bat`) with automatic venv/dependency setup.

## 2026-08-24 — Standalone demo dashboard
- Added `RecoverAI-standalone.html`, a single-file, same-origin demo dashboard served directly by the backend.

## 2026-08-25 — Agent safety, voice cockpit, recruiter hardening
- Hardened the bounded recovery agent: stopping rules, retry caps, idempotency, and additional safety tests.
- Built out the multi-language (8-language) voice recovery cockpit, including a live voice session workspace and consent-gated promise-to-pay capture.
- Added recruiter-facing proof layers: compliance scoring, cryptographically chained audit seals, health scoring, and customer 360 views.
- Aligned the React client with the recovery cockpit and added an idempotency key to React-driven executions.
- Final demo polish and benchmark tooling; published the React frontend client.

## Unreleased
- Empty `__init__.py` present in `tasks/` and `voice_providers/` for consistent package discovery.
- Added a dedicated `/api/health` endpoint for uptime checks (`scripts/health-check.js` previously relied on the root HTML route).
- Documented the `docker-compose.yml` frontend port (`3000:80`, nginx) to avoid confusion with the Vite dev server's `5173`.
- `start.sh` / `start.bat` now print a note when Razorpay keys are unset, making the simulated demo mode explicit at launch.

## 2026-09-01 — Security hardening pass
- Added API-key authorization (`X-API-Key`, `readonly`/`operator` roles) across the core API — cases, execution, voice events, audit, dashboard, and batch — leaving the public demo unauthenticated as before, but requiring keys once `APP_ENV=production`.
- The app now refuses to boot in production unless `API_KEYS` and `AUDIT_SIGNING_KEY` are configured, instead of silently running open or with a forgeable audit trail.
- The tamper-evident audit chain is now HMAC-SHA256 sealed (keyed with `AUDIT_SIGNING_KEY`) instead of a plain hash, so forging a self-consistent chain requires the signing secret, not just database write access.
- Bounded and sanitized the failure-reason text passed into the optional LLM diagnosis prompt as defense-in-depth against prompt injection.
- Patched known CVEs in pinned dependencies (`fastapi`, `starlette`, `pydantic`, `python-dotenv`, `pytest`, `razorpay`); `pip-audit` and `npm audit` now run clean.
- Added CI security scanning: `pip-audit`, `bandit`, `npm audit`, a Gitleaks secret scan, and Dependabot for pip/npm/GitHub Actions/Docker.
- Hardened both container images: non-root user and a `HEALTHCHECK` against the app's own liveness endpoint.
- Documented the new controls and an explicit in-scope/out-of-scope threat model in `docs/security.md`.
