import React from 'react';
import { money, pretty } from '../utils/format';
import { Badge } from './Badge';
import { RiskBadge } from './RiskBadge';

export function CaseDetailModal({ selected, cases, audit, detailLoading, copied, copyToClipboard, onClose }) {
  if (!selected) return null;
  const evidence = selected.evidence || {};
  const policyChecks = selected.policy_checks || {};
  const checkEntries = Object.entries(policyChecks);
  const hasEvidence = Object.keys(evidence).length > 0;
  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className="case-modal" onMouseDown={e => e.stopPropagation()} role="dialog" aria-label={'Case detail ' + selected.id}>
        <div className="modal-header">
          <div>
            <div className="eyebrow">Recovery case #{selected.id}</div>
            <h2>{selected.payment?.customer_name || selected.customer?.name || selected.customer_name || 'Customer'}</h2>
          </div>
          <button className="close-btn" onClick={onClose} aria-label="Close">×</button>
        </div>

        <div className="case-detail">
          <div><span>Amount</span><strong>{money(selected.amount ?? selected.payment?.amount)}</strong></div>
          <div><span>Status</span><Badge status={selected.status} /></div>
          <div><span>Risk level</span><RiskBadge risk={selected.risk_level} /></div>
          <div><span>Retry count</span><strong>{selected.retry_count}</strong></div>
        </div>

        <h3>Transaction ID</h3>
        <div className="tx-id-row">
          <code className="tx-id" id="tx-id-value">{selected.payment_id}</code>
          <button
            type="button"
            className={`copy-btn ${copied ? 'copied' : ''}`}
            onClick={() => copyToClipboard(selected.payment_id)}
            aria-label="Copy transaction ID"
            title={copied ? 'Copied!' : 'Copy'}
          >
            {copied ? '✓ Copied' : '⧉ Copy'}
          </button>
        </div>

        <h3>Failure code</h3>
        <div className="failure-code-row">
          <Badge status={selected.failure_category || 'unknown_failure'} />
          <span className="failure-reason">{selected.failure_reason || selected.payment?.failure_reason || 'No additional details recorded.'}</span>
        </div>

        <h3>Diagnosis</h3>
        <p>{selected.reason || selected.diagnosis || (detailLoading ? 'Loading the agent’s reasoning…' : 'Payment failure requires recovery review.')}</p>
        <h3>Recommended action</h3>
        <p>{pretty(selected.recommended_action)}</p>

        <h3>Agent reasoning</h3>
        {hasEvidence ? (
          <div className="agent-reasoning">
            <div className="case-detail">
              <div><span>Confidence</span><strong>{evidence.confidence != null ? `${Math.round(evidence.confidence * 100)}%` : '—'}</strong></div>
              <div><span>Diagnosis mode</span><strong>{pretty(evidence.diagnosis_mode || 'deterministic')}</strong></div>
              <div><span>Channel</span><strong>{pretty(evidence.channel || selected.recommended_action)}</strong></div>
              <div><span>Agent</span><strong>{evidence.agent || 'recoverai-bounded-agent'}</strong></div>
              <div><span>Payment history</span><strong>{evidence.total_payments ?? 0} total · {evidence.successful_payments ?? 0} succeeded · {evidence.previous_failures ?? 0} failed</strong></div>
              <div><span>Success rate</span><strong>{evidence.success_rate_percent != null ? `${evidence.success_rate_percent}%` : '—'}</strong></div>
            </div>
            {Array.isArray(evidence.stopping_rules) && evidence.stopping_rules.length > 0 && (
              <div className="stopping-rules">
                <span>Stopping rules (the agent will not act beyond these bounds)</span>
                <ul>{evidence.stopping_rules.map((rule, i) => <li key={i}>{rule}</li>)}</ul>
              </div>
            )}
          </div>
        ) : (
          <p className="muted">{detailLoading ? 'Loading evidence…' : 'No evidence recorded for this case yet.'}</p>
        )}

        <h3>Safety &amp; policy checks</h3>
        {checkEntries.length > 0 ? (
          <ul className="policy-check-list">
            {checkEntries.map(([name, passed]) => (
              <li key={name} className={passed ? 'check-pass' : 'check-fail'}>
                <span aria-hidden="true">{passed ? '✓' : '✗'}</span> {pretty(name.replace(/_check$/, ''))}
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">{detailLoading ? 'Loading policy checks…' : 'This case has not been through the policy gate yet — checks appear after the first execution attempt.'}</p>
        )}

        <h3>Retry sequencer</h3>
        <p>{selected.next_retry_at ? `Next policy-allowed retry: ${new Date(selected.next_retry_at).toLocaleString()}` : 'No retry scheduled; terminal or human review boundary applies.'}</p>
        <h3>Customer lifecycle</h3>
        <div className="lifecycle-timeline">
          {audit.filter(event => String(event.case_id) === String(selected.id)).slice(-6).map(event => <div key={event.id}><i /><div><strong>{pretty(event.event_type)}</strong><span>{event.timestamp ? new Date(event.timestamp).toLocaleString() : 'just now'}</span><small>{event.reason || event.action || 'Recorded'}</small></div></div>)}
          {!audit.some(event => String(event.case_id) === String(selected.id)) && <p>Timeline will populate after recovery actions.</p>}
        </div>
        <h3>Customer 360</h3>
        <div className="customer-history">{cases.filter(item => (item.customer?.id || item.customer_id || item.customer_name) === (selected.customer?.id || selected.customer_id || selected.customer_name)).slice(0, 5).map(item => <div key={item.id}><strong>{money(item.amount)}</strong><span>{pretty(item.status)} · {pretty(item.failure_category || 'payment')}</span></div>)}</div>
      </div>
    </div>
  );
}
