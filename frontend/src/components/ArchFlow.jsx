import React from 'react';

export function ArchFlow() {
  return (
    <section className="arch-flow">
      <div><strong>AI recommendation</strong><span>LLM proposes the action.</span></div>
      <b>→</b>
      <div><strong>Policy engine</strong><span>Backend gates the action.</span></div>
      <b>→</b>
      <div><strong>Razorpay Test Mode</strong><span>Bounded execution.</span></div>
      <b>→</b>
      <div><strong>Audit trail</strong><span>Every decision is explainable.</span></div>
    </section>
  );
}
