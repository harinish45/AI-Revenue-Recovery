# RecoverAI Agent Architecture

RecoverAI is a bounded revenue-recovery agent. It can detect risk, explain a
decision, request an approved intervention, and measure the result. It cannot
invent actions, bypass policy, or move production money.

```text
Payment / checkout signal
        |
        v
Risk detector -> Evidence builder -> Intervention planner
                                      |
                                      v
                           Policy + stopping-rule gate
                              /                  \
                     approved action          human review
                              |                  |
                              v                  v
                    Test-mode provider      Escalation queue
                              |
                              v
                     Outcome + metrics
                              |
                              v
                    Append-only audit chain
```

## Agent contract

The planner returns a typed decision containing:

- root-cause category and risk level;
- approved intervention and channel;
- confidence score;
- human-readable rationale;
- explicit stopping rules.

The current planner is deterministic so the demo is reproducible. It is
designed as a replaceable policy-safe seam for a model-backed planner later.
The model would propose; the policy engine would still authorize.

## Safety gates

Every execution checks terminal state, retry budget, amount threshold, payment
eligibility, action allowlist, confidence threshold, and presence of stopping
rules. Invalid instruments and low-confidence decisions escalate instead of
retrying. Repeated HTTP requests with the same `Idempotency-Key` return the
original result without creating another execution.

Every route that can read case data or trigger an intervention sits behind an
API-key authorization boundary (`backend/app/security/auth.py`), and every
audit event is sealed with an HMAC keyed by `AUDIT_SIGNING_KEY` — the agent's
decisions are not just policy-gated, the record of them is tamper-evident
against anyone without that key. See `docs/security.md` for the full model.

## Demo scenarios

The seeded dataset covers gateway timeout, insufficient funds, bank rejection,
invalid instrument, and checkout abandonment. The UI's existing batch flow
shows amount at risk, attempts, recovered amount, failures, and escalation.
The failure simulation demonstrates a bounded stop and human handoff.

## Recruiter proof points

- Measured batch recovery instead of classification-only output.
- Explicit audit events for detection, analysis, policy, execution, outcome,
  and escalation.
- Test-mode-only provider behavior when credentials are absent.
- Provider failures do not leak secrets or stack traces through the API.
- Frontend is a consumer of the contract; authorization and safety live in the
  backend.

## Extension path

The same contract can support overdue receivables, mandate retry sequencing,
promise-to-pay tracking, and compliant multilingual voice messages (the voice
cockpit already covers 8 Indian languages, including code-switched Hinglish).
Each new intervention must be added to the action allowlist with its own
channel, consent rules, retry budget, and escalation condition.
