import React from 'react';
import { money } from '../utils/format';

export function BatchResultModal({ batchResult, progress, onClose }) {
  if (!batchResult) return null;
  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className={`case-modal batch-modal ${progress === 100 ? 'complete' : ''}`} onMouseDown={e => e.stopPropagation()} role="dialog" aria-label="Batch recovery result">
        <div className="modal-header">
          <div>
            <div className="eyebrow">Batch recovery result</div>
            <h2>Revenue recovery completed</h2>
          </div>
          <button className="close-btn" onClick={onClose} aria-label="Close">×</button>
        </div>
        <div className="batch-grid">
          <div><span>Cases</span><strong>{batchResult.total_cases}</strong></div>
          <div><span>Attempted</span><strong>{batchResult.attempted}</strong></div>
          <div><span>Successful</span><strong className="positive">{batchResult.successful}</strong></div>
          <div><span>Failed</span><strong className="negative">{batchResult.failed}</strong></div>
          <div><span>Escalated</span><strong className="negative">{batchResult.escalated}</strong></div>
          <div><span>Smart skipped</span><strong>{batchResult.skipped || 0}</strong></div>
          <div><span>Amount at risk</span><strong>{money(batchResult.amount_at_risk)}</strong></div>
          <div><span>Amount recovered</span><strong className="positive">{money(batchResult.amount_recovered)}</strong></div>
          <div><span>Estimated cost</span><strong>{money(batchResult.estimated_cost)}</strong></div>
          <div><span>Net recovered</span><strong className="positive">{money(batchResult.net_recovered)}</strong></div>
          <div><span>Recovery rate</span><strong>{batchResult.recovery_rate}%</strong></div>
        </div>
        {Number(batchResult.skipped || 0) > 0 && <div className="smart-skip-note"><strong>Smart skip protected unit economics</strong><span>{batchResult.skipped} case{batchResult.skipped === 1 ? '' : 's'} were not contacted because the expected recovery value did not justify the intervention cost. This keeps the agent bounded and net-recovery positive.</span></div>}
        <p className="modal-footnote">Backend batch metrics · Razorpay Test Mode · bounded recovery workflow.</p>
      </div>
    </div>
  );
}
