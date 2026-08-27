"""Free neural English narration for the real website capture."""
import asyncio
import subprocess
from pathlib import Path

OUT = Path(__file__).parent / "real-website-capture"
VOICE = "rms"  # free local male voice bundled with FFmpeg/libflite
SEGMENTS = [
    (45, "Revenue loss rarely arrives as one clean failure. A payment degrades, a checkout is abandoned, a subscription retry fails, or an invoice quietly becomes overdue. This is RecoverAI, an AI revenue recovery agent for Razorpay Test Mode. The banner is intentional: we are not using real payment credentials or moving real money. Our dataset is randomly generated for a safe buildathon demonstration. I will show the complete loop: detect the risk, diagnose the reason, choose a bounded intervention, and prove the result. The dashboard starts with the business view: money at risk, money recovered, recovery rate, open cases, and human escalations. Every number comes from the live backend."),
    (50, "I am opening Cases now. This is where payment signals become operational work. Each case has an identifier, customer, amount, failure category, risk, compliance score, and current status. The Focus tool highlights the control I am explaining while I record. I can filter by high risk, medium risk, or low risk, and I can switch status between open, recovered, human review, and skipped. I am inspecting a case to see the evidence: the gateway signal, the likely root cause, retry history, amount, and recommended action. RecoverAI can use an optional structured model adapter for diagnosis, but a deterministic fallback is always available. The model can recommend; the policy engine decides what may execute."),
    (50, "Now I am running Batch Recovery on the real seeded queue. Watch the pipeline move through detection, diagnosis, decision, policy gate, and execution. The result is not just a success message. It reports recovered cases, escalations, smart skips, estimated contact cost, gross recovery, and net recovery. Smart skip is important: if the expected recovery is lower than the cost of contacting the customer, the agent stops and explains why. Retry caps, amount ceilings, rate limits, and idempotency keys prevent uncontrolled automation. This is how the agent demonstrates measurable money recovered across a batch while respecting a stopping rule."),
    (50, "Next is the safety path. I reset the synthetic dataset, arm the deterministic failure simulation, and execute one open case. The result modal clearly changes from Executing to Result and says Needs Human Review. The Cases table then reflects the escalated status, and the action changes from Execute to Done. That behavior is deliberate. A failed intervention is not treated as permission to retry forever. The system preserves the case evidence and gives a human the decision path. This is a real backend response in Test Mode, with the same policy and audit behavior used by the application—not a fake animation."),
    (55, "The Voice Agent brings the same boundaries into a customer conversation. It supports English, Hindi and Hinglish, Tamil, Kannada, Telugu, Marathi, Bengali, and Malayalam. I select English here, choose a case, and confirm the operator consent gate. The interface does not unlock Start Call until consent is checked. In a real conversation, a customer saying haan bolo can receive a secure payment-link path. A customer saying balance nahi can receive one callback option instead of repeated pressure. The agent captures structured intent such as promise to pay, dispute, callback, or refusal. This demo uses browser and Test Mode simulation; live voice providers can be connected through the provider adapter boundary. Consent, call outcome, and promises are written to the same audit trail."),
    (50, "Finally, I am opening Audit Trail. Here the agent becomes inspectable. We can follow detection, diagnosis, policy decision, execution, escalation, and voice events with an actor, timestamp, case reference, and chained SHA-256 seal. I can verify a seal and export the record as JSON or CSV. Webhook signatures, replay-age checks, deduplication, consent gates, rate limits, and idempotency protect the edges. So the value proposition is simple: RecoverAI does more than identify revenue at risk. It makes the safest useful decision, recovers measurable value in a controlled environment, and leaves evidence behind. The numbers here are random Test Mode data, but the workflow, policy boundaries, state transitions, and audit behavior are real. This is revenue recovery with an accountable agent loop."),
]

async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    wavs = []
    for i, (seconds, text) in enumerate(SEGMENTS, 1):
        textfile = OUT / f"voice-{i}.txt"
        wav = OUT / f"voice-{i}.wav"
        textfile.write_text(text, encoding="utf-8")
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"flite=textfile=voice-{i}.txt:voice={VOICE}", "-af", f"apad,atrim=duration={seconds}", "-ar", "48000", "-ac", "2", str(wav)], check=True, cwd=OUT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wavs.append(wav)
    concat = OUT / "voice-concat.txt"
    concat.write_text("\n".join(f"file '{p.as_posix()}'" for p in wavs), encoding="utf-8")
    output = OUT / "narration-neural.wav"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(output)], check=True)
    print(output)

asyncio.run(main())
