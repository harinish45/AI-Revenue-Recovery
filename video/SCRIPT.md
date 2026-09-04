# RecoverAI — 5:00 Pitch Video Script (presenter-read, screen recording)

**Target runtime:** 300 seconds (5:00). Every beat below names the exact
screen to be on, the exact thing to click, and what to say while you click
it — read this like a shot list, not an essay. Speak at a normal,
confident pace; don't rush the numbers.

This replaces the old 4:30 script. The product changed enough since that
one was written (nav renamed, Smart Collect rebuilt, voice agent
understands a lot more real sentences now, README reordered) that a patch
wouldn't have held together — this is a full rewrite grounded in the
actual current UI, button-for-button.

---

## Before you hit record

- **Browser: Microsoft Edge.** It ships the best built-in neural voices for
  the 8 languages — Chrome often has gaps. This matters for the voice
  section sounding good on camera.
- **Reset the data right before recording.** Settings → Data → **Reset
  All**, confirm it. You want a clean, believable dataset, not whatever
  state you left mid-testing.
- **Have one open, high-risk case ID memorized or written down** (any row
  in Transactions with status "Open" works) — you'll execute it live in
  Beat 4.
- **Close any dev tools / console** so the recording is just the product.
- **Do a dry run of Beat 5 (voice) once before recording** — the first
  mic permission prompt from the browser will otherwise eat your take.

---

## 0:00–0:20 — Open (20s)

**Screen:** Home (the app opens here — KPI cards across the top).

**Do:** Nothing yet. Let the dashboard sit on screen for a beat before you
start talking.

**Say:**
> Every merchant loses money to payments that just... fail. A UPI decline,
> a timeout, a card that got rejected. Most of that money is recoverable —
> but only if something acts on it fast, safely, and without guessing.
> This is RecoverAI. It's running live right now, in Razorpay Test Mode —
> no real money moves, but everything else you're about to see is real.

---

## 0:20–1:00 — Detect: the dashboard (40s)

**Screen:** Home.

**Do:** Point at the five KPI cards left to right — **At Risk**,
**Recovered**, **Rate**, **Open**, **Escalated** — then scroll to
**Agent Activity** and **Human Review** below.

**Say:**
> These five numbers aren't decoration — they're the live output of the
> agent's backend, pulled straight from the database on every load. At
> Risk is money sitting in open cases right now. Recovered is money a
> payment provider has actually confirmed — not money we sent a link for
> and hoped. Down here, Agent Activity is a real-time feed of every
> decision the system has made, and Human Review is the queue it's
> deliberately keeping a person in the loop on.

---

## 1:00–1:45 — Diagnose: Transactions (45s)

**Screen:** Click **Transactions** in the sidebar.

**Do:** Set the **Risk** filter to "High". Click any row to open its case
detail.

**Say:**
> This is where a failed payment becomes a case the agent can reason
> about. I'll filter to high-risk. Each one carries an amount, a
> diagnosis, and a recommended action — and if I open one, you can see
> the evidence behind it: the customer's actual payment history, the
> policy checks it has to clear, and why this specific case is sitting
> here. The agent doesn't just guess a category — it scores confidence
> from real evidence, and a separate, deterministic policy engine decides
> what's actually allowed to run. The model can recommend. It cannot
> approve itself.

**Do:** Close the case detail.

---

## 1:45–2:35 — Decide and recover: Batch Run (50s)

**Screen:** Click **Batch Run** in the sidebar.

**Do:** Click **Start Batch** (or **Run Batch Recovery** if you're doing
this from Home instead). Let it run to completion — watch the log stream.

**Say:**
> Now watch it work an entire queue at once. Every case goes through the
> same pipeline — detect, diagnose, decide, execute — one policy gate at
> a time. When it finishes, it doesn't just say "done." It tells you
> exactly what happened: how many recovered, how many escalated, how many
> it deliberately skipped. That skip number matters — if the cost of
> contacting a customer is higher than what we'd realistically recover, the
> agent stops itself and says so, right here in the economics panel.
> That's a stopping rule, not an afterthought.

**Do:** Point at the **Recovery Economics** panel — Gross recovered / Est.
contact cost / Net recovered.

**Say:**
> Gross recovered, contact cost, net recovered — the actual math, not a
> vanity number.

---

## 2:35–3:05 — Contain failure: escalation on purpose (30s)

**Screen:** Home.

**Do:** Toggle **Arm Failure Sim** on. Go to **Transactions**, find your
one memorized open case, click **Execute** on that row.

**Say:**
> Now I'll deliberately force a failure — this switch injects one, but
> only after the policy gate has already approved the action, so we're
> testing the real failure path, not faking it. Watch the result.

**Do:** Let the result modal resolve — it should read something like
"NEEDS HUMAN REVIEW."

**Say:**
> It doesn't retry blindly. It escalates, hands off to a human with the
> full evidence trail intact, and that case is now closed to further
> automated action — the Execute button is gone for it. Escalation is a
> designed outcome here, not an error screen.

**Do:** Toggle **Arm Failure Sim** back off before moving on.

---

## 3:05–4:00 — Smart Collect: the voice agent (55s)

**Screen:** Click **Smart Collect** in the sidebar.

**Do:** Pick any open case card. On the setup screen, check the consent
box, click **Start Voice Call**.

**Say:**
> This is the part people don't expect from a payments dashboard — a real
> voice conversation, in eight Indian languages, that a customer can
> actually talk to. Nothing starts without this consent checkbox — it's
> not a UI suggestion, the call literally cannot begin without it.

**Do:** Once the call is live, type into the reply box — don't use a
quick-reply button — something like **"how much do I owe"** and send it.

**Say:**
> I'm not going to tap one of the suggested replies — I want to type
> something myself, in my own words, to prove this isn't just a
> button-triggered script.

**Do:** Let the agent respond — it should recap the real case amount.

**Say:**
> Notice it just quoted the actual amount from this specific case, live —
> that's not a canned line, it pulled the real number off the case
> object. It understands intent, not just exact phrases: someone asking
> for a discount, disputing the charge, saying they lost their job, giving
> the wrong-person response — each one gets handled differently, and every
> one of those outcomes gets written to the same audit trail as everything
> else in this app.

**Do:** Click **End call**.

---

## 4:00–4:40 — Prove: Audit Trail (40s)

**Screen:** Click **Audit Trail** in the sidebar.

**Do:** Scroll the event list briefly. Click **Verify Chain**.

**Say:**
> Every single thing you've just watched — the batch run, the escalation,
> that voice call — wrote a sealed event here. Each one is chained to the
> one before it with a SHA-256 hash. I'll verify the whole chain right
> now, live.

**Do:** Point at the green **"✓ Chain verified"** badge that appears next
to the button once it resolves.

**Say:**
> Every sealed event, recomputed and matched, root to tip. If a single
> byte of this history had been altered, or even if someone deleted just
> the newest event and left the rest untouched, this check would catch
> it. That's the difference between a dashboard that claims to be safe
> and one that can prove it, on demand, to anyone.

---

## 4:40–5:00 — Close (20s)

**Screen:** Back to Home.

**Do:** Let the KPI cards sit on screen one more time.

**Say:**
> RecoverAI doesn't just flag revenue at risk — it makes the safest useful
> decision, recovers real measurable value, and leaves proof behind for
> every step. Detect, diagnose, decide, recover, audit. That's an agent
> that earns the right to act, every single time.

---

## Notes for the next take

- If a language voice sounds off on your device, that's expected and
  already handled in-product — the app shows text instead of bad audio
  rather than hiding the gap. Don't apologize for it on camera; if you
  want to mention it, frame it as the honesty feature it is.
- If you want a second language moment for variety, switch the Smart
  Collect language selector to Hindi *before* Beat 5 instead of adding
  time inside it — showing the label and greeting change is proof enough
  without spending narration time on it.
- Keep Beat 5's typed line real and unscripted-sounding on camera — that's
  the single strongest "this actually works" moment in the whole video,
  don't rush past it.
