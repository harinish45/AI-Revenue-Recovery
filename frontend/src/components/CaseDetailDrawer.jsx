import React, { useEffect, useState } from 'react';
import { X, Play, Brain, Shield, ChevronRight } from 'lucide-react';
import { api } from '../services/api';

function formatINR(v) {
  return v?.toLocaleString('en-IN', { minimumFractionDigits: 2 }) ?? '0.00';
}

function StatusBadge({ status }) {
  const s = (status || '').toLowerCase();
  return <span className={`status-badge status-badge--${s}`}>{status?.replace('_', ' ')}</span>;
}

function Field({ label, value }) {
  return (
    <div className="case-field">
      <span className="case-field-label">{label}</span>
      <span className="case-field-value">{value ?? '—'}</span>
    </div>
  );
}

export default function CaseDetailDrawer({ caseId, onClose, onExecute }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [executing, setExecuting] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const data = await api.getCase(caseId);
        setDetail(data);
      } catch (err) {
        setError(err?.error?.message || 'Failed to load case');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [caseId]);

  const handleExecute = async () => {
    setExecuting(true);
    await onExecute(caseId);
    // Refresh detail
    const updated = await api.getCase(caseId);
    setDetail(updated);
    setExecuting(false);
  };

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <div className="drawer" role="dialog" aria-modal="true">
        <div className="drawer-header">
          <div className="drawer-title">
            <ChevronRight size={16} style={{ color: 'var(--color-accent)' }} />
            Case #{caseId}
            {detail && <StatusBadge status={detail.status} />}
          </div>
          <button className="btn btn--ghost btn--sm" onClick={onClose}>
            <X size={14} /> Close
          </button>
        </div>

        <div className="drawer-body">
          {loading && (
            <div className="loading-container"><div className="spinner" /></div>
          )}

          {error && (
            <div className="error-banner">{error}</div>
          )}

          {detail && !loading && (
            <>
              {/* Execute button */}
              {detail.status === 'OPEN' && (
                <div style={{ marginBottom: 'var(--space-5)' }}>
                  <button
                    className={`btn btn--primary btn--lg ${executing ? 'btn--loading' : ''}`}
                    onClick={handleExecute}
                    disabled={executing}
                    style={{ width: '100%', justifyContent: 'center' }}
                    id={`detail-execute-${caseId}`}
                  >
                    {executing ? (
                      <span style={{ animation: 'spin 0.8s linear infinite', display: 'inline-block', marginRight: 8 }}>⟳</span>
                    ) : <Play size={14} />}
                    Execute Recovery Action
                  </button>
                </div>
              )}

              {/* Payment Details */}
              <div className="case-section">
                <div className="case-section-title">Payment Details</div>
                <Field label="Transaction ID" value={
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--color-accent-light)' }}>
                    {detail.payment?.transaction_id}
                  </span>
                } />
                <Field label="Customer" value={detail.payment?.customer_name} />
                <Field label="Email" value={detail.payment?.customer_email} />
                <Field label="Phone" value={detail.payment?.customer_phone} />
                <Field label="Amount" value={<strong>₹{formatINR(detail.payment?.amount)}</strong>} />
                <Field label="Status" value={<StatusBadge status={detail.payment?.status} />} />
                <Field label="Failure Code" value={
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--color-warning)' }}>
                    {detail.payment?.failure_code}
                  </span>
                } />
              </div>

              {/* AI Diagnosis */}
              <div className="case-section">
                <div className="case-section-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Brain size={12} /> AI Diagnosis
                </div>
                <div className="case-diagnosis-box">
                  <div className="case-diagnosis-text">{detail.diagnosis}</div>
                  {detail.evidence && detail.evidence.length > 0 && (
                    <ul className="evidence-list">
                      {detail.evidence.map((e, i) => (
                        <li key={i} className="evidence-item">{e}</li>
                      ))}
                    </ul>
                  )}
                  <div className="confidence-bar">
                    <div className="confidence-label">
                      <span>AI Confidence</span>
                      <strong style={{ color: 'var(--color-text-primary)' }}>
                        {((detail.confidence || 0) * 100).toFixed(0)}%
                      </strong>
                    </div>
                    <div className="confidence-track">
                      <div
                        className="confidence-fill"
                        style={{ width: `${(detail.confidence || 0) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Policy & Recovery */}
              <div className="case-section">
                <div className="case-section-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Shield size={12} /> Policy & Recovery
                </div>
                <Field label="Recommended Action" value={detail.recommended_action} />
                <Field label="Risk Level" value={
                  <span className={`risk-badge risk-badge--${(detail.risk_level || 'medium').toLowerCase()}`}>
                    {detail.risk_level}
                  </span>
                } />
                <Field label="Attempt Count" value={detail.attempt_count} />
                <Field label="Retry Count" value={detail.retry_count} />
                <Field label="Recovered" value={<strong style={{ color: 'var(--color-success)' }}>₹{formatINR(detail.amount_recovered)}</strong>} />
              </div>

              {/* Execution History */}
              {detail.executions && detail.executions.length > 0 && (
                <div className="case-section">
                  <div className="case-section-title">Execution History</div>
                  {detail.executions.map(exec => (
                    <div key={exec.id} style={{
                      background: 'var(--color-bg-base)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-sm)',
                      padding: 'var(--space-3)',
                      marginBottom: 'var(--space-2)',
                      fontSize: '12px',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <strong style={{ fontFamily: 'var(--font-mono)' }}>{exec.action_taken}</strong>
                        <span style={{ color: 'var(--color-text-muted)' }}>
                          {new Date(exec.timestamp).toLocaleString('en-IN')}
                        </span>
                      </div>
                      <div style={{ color: exec.result?.includes('SUCCESS') ? 'var(--color-success)' : 'var(--color-danger)' }}>
                        {exec.result}
                      </div>
                      {exec.amount_recovered > 0 && (
                        <div style={{ color: 'var(--color-success)', marginTop: 4 }}>
                          Recovered: ₹{formatINR(exec.amount_recovered)}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}
