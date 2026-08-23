import React, { useState } from 'react';
import { Play, List } from 'lucide-react';

function formatINR(amount) {
  return amount?.toLocaleString('en-IN', { minimumFractionDigits: 2 }) ?? '0.00';
}

function StatusBadge({ status }) {
  const s = (status || '').toLowerCase();
  return (
    <span className={`status-badge status-badge--${s}`}>
      {status?.replace('_', ' ')}
    </span>
  );
}

function RiskBadge({ risk }) {
  const r = (risk || 'medium').toLowerCase();
  return <span className={`risk-badge risk-badge--${r}`}>{risk}</span>;
}

const ACTION_LABELS = {
  SEND_RETRY_LINK: 'Retry Link',
  OFFER_SPLIT_PAYMENT: 'Split Payment',
  HALT_AND_ALERT: 'Halt & Alert',
  REQUEST_CARD_UPDATE: 'Card Update',
  SEND_REMINDER_NUDGE: 'Nudge',
  ESCALATE_TO_HUMAN: 'Escalate',
  PENDING: 'Pending',
};

export default function CasesTable({ cases, onSelectCase, onExecute }) {
  const [executingId, setExecutingId] = useState(null);

  const handleExecute = async (e, caseId) => {
    e.stopPropagation();
    setExecutingId(caseId);
    try {
      await onExecute(caseId);
    } finally {
      setExecutingId(null);
    }
  };

  return (
    <div>
      <div className="section-header">
        <div className="section-title">
          <List size={16} />
          Recovery Cases
        </div>
        <span className="table-count">{cases.length} total</span>
      </div>

      <div className="table-container">
        {cases.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon"><List size={48} /></div>
            <div className="empty-state-title">No Recovery Cases</div>
            <div className="empty-state-text">Click "Seed Demo Data" to generate 100 payment failure cases.</div>
          </div>
        ) : (
          <div className="table-overflow">
            <table>
              <thead>
                <tr>
                  <th>Case ID</th>
                  <th>Customer</th>
                  <th>Transaction ID</th>
                  <th>Amount (INR)</th>
                  <th>Failure</th>
                  <th>AI Recommendation</th>
                  <th>Risk</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {cases.map(c => (
                  <tr key={c.id} onClick={() => onSelectCase(c)}>
                    <td className="td-mono">#{c.id}</td>
                    <td>
                      <div className="td-primary">{c.payment?.customer_name || '—'}</div>
                      <div style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
                        {c.payment?.customer_email}
                      </div>
                    </td>
                    <td className="td-mono">{c.payment?.transaction_id || '—'}</td>
                    <td className="td-amount">₹{formatINR(c.payment?.amount)}</td>
                    <td>
                      <span style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '11px',
                        color: 'var(--color-warning)',
                        background: 'rgba(245,166,35,0.1)',
                        padding: '2px 6px',
                        borderRadius: '4px',
                      }}>
                        {c.payment?.failure_code || '—'}
                      </span>
                    </td>
                    <td style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                      {ACTION_LABELS[c.recommended_action] || c.recommended_action || '—'}
                    </td>
                    <td><RiskBadge risk={c.risk_level} /></td>
                    <td><StatusBadge status={c.status} /></td>
                    <td onClick={e => e.stopPropagation()}>
                      {c.status === 'OPEN' ? (
                        <button
                          className="btn btn--primary btn--sm"
                          disabled={executingId === c.id}
                          onClick={e => handleExecute(e, c.id)}
                          id={`execute-case-${c.id}`}
                        >
                          {executingId === c.id ? (
                            <span style={{ animation: 'spin 0.8s linear infinite', display: 'inline-block' }}>⟳</span>
                          ) : (
                            <Play size={12} />
                          )}
                          Execute
                        </button>
                      ) : (
                        <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
