# Security and Reliability Controls

RecoverAI is a Razorpay Test Mode / simulated-gateway demo. Production keys
and production money movement are out of scope.

Implemented controls:

1. Secrets are read from environment configuration; no credentials are
   committed or returned in API errors.
2. CORS is explicit and configurable rather than wildcard.
3. Responses include request correlation IDs and browser hardening headers.
4. Pagination has server-side bounds to prevent unbounded database reads.
5. Execution is idempotent when clients supply `Idempotency-Key`.
6. Amount and retry limits are configuration-driven policy gates.
7. Interventions are allowlisted; missing confidence or stopping rules block
   automation.
8. Audit events receive chained, **HMAC-SHA256** seals (keyed with
   `AUDIT_SIGNING_KEY`), allowing tamper evidence to be checked independently
   of the UI. Because the seal is keyed, forging a self-consistent chain
   requires the signing secret, not just database write access — a plain
   (unkeyed) hash would let anyone who can write to the database recompute a
   chain that still verifies.
9. Missing payment records, invalid instruments, provider failures, and
   simulated gateway failures stop safely and escalate.
10. The frontend is never treated as an authorization boundary. Requests to
    every core API route (`cases`, `execution`, `voice-events`, `audit`,
    `dashboard`, `batch`) are authorized server-side via `X-API-Key`
    (see control 13); the frontend is a client of that boundary, not part of
    it.
11. Webhooks verify the exact raw request body when a secret is configured and
    deduplicate provider event IDs.
12. Idempotency responses are bound to their original case, and audit seal
    verification recomputes the event hash before reporting success.
13. **API-key authorization** (`backend/app/security/auth.py`) gates the core
    API with two roles: `readonly` (dashboard/cases/audit reads) and
    `operator` (execution, payment confirmation, voice events — anything that
    can move a case toward counted revenue). Configured via `API_KEYS`
    (`"<key>:<role>"` entries). Webhook and demo-control routes keep their own
    separate, existing mechanisms (HMAC signature, `X-Demo-Token`).
14. **Fail-closed startup in production.** `APP_ENV=production` refuses to
    boot unless both `API_KEYS` and `AUDIT_SIGNING_KEY` are configured — the
    app cannot be silently deployed wide-open or with a forgeable audit trail.
    Outside production, both stay optional so the public demo and local dev
    keep working exactly as before this control was added (an unset
    `AUDIT_SIGNING_KEY` falls back to a random per-process key).
15. **Model-assisted diagnosis input hardening**
    (`backend/app/services/diagnosis_service.py`): the failure-reason text
    interpolated into the LLM prompt is treated as untrusted third-party data,
    truncated, and stripped of control/newline characters before being sent.
    The real safety boundary is still that the model's suggested action is
    validated against an allowlist before it can influence execution — this is
    defense-in-depth on the input side.
16. **CI security scanning**: `pip-audit` (Python dependency CVEs), `npm audit`
    (JS dependency CVEs), `bandit` (Python SAST), and a Gitleaks secret scan
    all run on every push/PR, plus Dependabot for pip, npm, GitHub Actions, and
    Docker base images.
17. Both container images run as an unprivileged user and expose a
    `HEALTHCHECK` against the app's own health/liveness endpoint.

## Threat model — in scope vs. out of scope

**In scope / mitigated by the above:** unauthorized reads or writes to the
core API from an untrusted network position, forged or replayed webhooks,
double-execution of a recovery action, policy bypass via a crafted request,
undetected tampering with the audit trail by someone with database access,
known-CVE dependencies, and committed secrets.

**Explicitly out of scope for this demo repo** (call these out before treating
a deployment as production-ready): TLS termination (assumed to be handled by
the hosting platform / a reverse proxy), a full identity provider or per-user
accounts (API keys here are shared bearer credentials per role, not
individual identities), distributed rate limiting across multiple app
instances (the in-process limiter does not share state across replicas),
SQLite as the datastore (fine for a demo; use PostgreSQL with TLS in
production), and secret storage (env vars here; use a real secret manager in
production).

For a deployed environment: set a strict `CORS_ORIGINS`, disable demo routes
(`DEMO_MODE=false`), set `APP_ENV=production` with `API_KEYS` and
`AUDIT_SIGNING_KEY` configured, use PostgreSQL with TLS, store secrets in a
secret manager, and add distributed rate limiting (e.g. a Redis-backed
limiter) if running more than one instance.
