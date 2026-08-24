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
8. Audit events receive chained SHA-256 seals, allowing tamper evidence to be
   checked independently of the UI.
9. Missing payment records, invalid instruments, provider failures, and
   simulated gateway failures stop safely and escalate.
10. The frontend is never treated as an authorization boundary.

For a deployed environment, set a strict `CORS_ORIGINS`, disable `DEMO_MODE`,
configure a real authentication layer/API gateway, use PostgreSQL with TLS,
store secrets in a secret manager, and add distributed rate limiting.
