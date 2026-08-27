# RecoverAI — Locked 4:30 English Narration

**Target runtime:** 270 seconds exactly. Read at a measured pace with short pauses between sections. Captions should mirror the spoken words.

## 0:00–0:20 — The leak

Revenue loss rarely arrives as one clean failure. A payment degrades, a checkout is abandoned, a subscription retry fails, or an invoice quietly becomes overdue. RecoverAI closes that loop: it detects the risk, understands the reason, chooses a bounded intervention, and proves what happened. This demo is safely running in Razorpay Test Mode with simulated gateway behavior.

## 0:20–0:55 — Detect

I’ll start by seeding a realistic recovery queue. At the top, the dashboard makes the business impact visible immediately: money at risk, money recovered, recovery rate, open cases, and escalations. These are not decorative counters. They are the outcome surface for the agent. Each case carries amount, risk, failure signal, customer context, and a next best action. The agent is not just finding a problem; it is turning an uncertain signal into an accountable work item.

## 0:55–1:35 — Diagnose

Now I’ll open the Cases workspace. The compact risk and status selectors let an operator move from the full queue to exactly the work that needs attention. I can isolate high-risk cases, recovered cases, skipped cases, or human review. When I inspect a case, the panel shows the evidence behind the decision: the payment signal, likely root cause, amount, retry history, policy boundary, and recommended intervention. An optional structured language-model adapter can enrich diagnosis, but the deterministic fallback remains available, and execution is always policy-gated. That is the important distinction: intelligence can recommend, but policy controls what may happen.

## 1:35–2:20 — Decide and recover

Next, I’ll run the recovery batch. The workflow moves through detection, diagnosis, decision, policy gate, and execution. The progress state is visible, and the result reports recovered value, escalated cases, smart skips, estimated cost, and net recovery. Smart skip is deliberate: if an intervention costs more than the expected recovery, the agent stops and explains why. This is where the demo becomes measurable. We can compare gross recovery with intervention cost instead of claiming success from activity alone. Retry counts, amount ceilings, idempotency keys, and rate limits keep the automation bounded.

## 2:20–3:00 — Contain failure

Now I’ll demonstrate the safety path. I arm the deterministic failure simulation, then execute one open case. The result is no longer hidden behind a generic error. The modal clearly changes from execution to result and shows that the case was escalated to human review. The case list reflects that terminal status, and the Execute action is no longer available for a closed case. This is a small interaction with a big signal: the agent understands that escalation is an outcome, not an invitation to retry forever. A human can take over with the full evidence intact.

## 3:00–3:55 — Human voice

The voice workspace brings the same policy boundary into the customer conversation. Before a call starts, consent is explicit and confirmed in both the interface and the backend. The agent supports English, Hindi and Hinglish, Tamil, Kannada, Telugu, Marathi, Bengali, and Malayalam. In this example, the customer says, “haan bolo,” and the agent can offer a payment link. If the customer says, “balance nahi,” the system can capture a callback or promise instead of pressuring them. The important output is structured intent: promise to pay, dispute, callback, or escalation. Ending the call writes the event to the same audit trail, so the conversation is connected to the recovery case rather than disappearing into a transcript.

## 3:55–4:25 — Prove

Finally, I’ll open the compliance audit. Here we can follow the chain from detection to diagnosis, decision, execution, escalation, and voice interaction. Each meaningful event carries an actor, timestamp, case reference, and chained SHA-256 seal. The seal can be verified, and the record can be exported as JSON or CSV. Webhook signatures, replay-age checks, deduplication, consent gates, and idempotency protect the edges of the workflow. The result is an agent that is useful, measurable, and inspectable.

## 4:25–4:30 — Close

RecoverAI does more than identify revenue at risk. It makes the safest useful decision, recovers measurable value, and leaves evidence behind. That is revenue recovery with an accountable agent loop.
