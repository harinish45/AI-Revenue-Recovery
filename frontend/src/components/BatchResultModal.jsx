import React from 'react';
import { X, TrendingUp, CheckCircle2, XCircle, AlertTriangle, Users } from 'lucide-react';

function formatINR(v) {
  return v?.toLocaleString('en-IN', { minimumFractionDigits: 2 }) ?? '0.00';
}

export default function BatchResultModal({ result, onClose }) {
  if (!result) return null;
  const rate = result.recovery_rate_percent || 0;

  return (
    <div className="modal-overlay">
      <div className="modal">
        <div className="modal-header">
          <div className="modal-title">
            <TrendingUp size={20} style={{ color: 'var(--color-success)' }} />
            Batch Recovery Complete
          </div>
          <button className="btn btn--ghost btn--sm" onClick={onClose}>
            <X size={14} />
          </button>
        </div>

        <div className="modal-body">
          {/* Hero: amount recovered */}
          <div className="batch-recovery-hero">
            <div className="batch-recovery-amount">
              ₹{formatINR(result.amount_recovered)}
            </div>
            <div className="batch-recovery-label">
              Recovered across {result.successful} successful cases
            </div>
            <div className="batch-rate-bar" style={{ margin: 'var(--space-3) 0 0' }}>
              <div className="batch-rate-fill" style={{ width: `${Math.min(rate, 100)}%` }} />
            </div>
            <div style={{ fontSize: '13px', color: 'var(--color-success)', marginTop: 'var(--space-1)' }}>
              {rate.toFixed(1)}% recovery rate
            </div>
          </div>

          {/* Stats grid */}
          <div className="batch-stat-grid">
            <div className="batch-stat">
              <div className="batch-stat-value">{result.total_cases}</div>
              <div className="batch-stat-label">Total Cases</div>
            </div>
            <div className="batch-stat">
              <div className="batch-stat-value">{result.attempted}</div>
              <div className="batch-stat-label">Attempted</div>
            </div>
            <div className="batch-stat" style={{ borderColor: 'var(--color-success)' }}>
              <div className="batch-stat-value" style={{ color: 'var(--color-success)' }}>
                <CheckCircle2 size={18} style={{ display: 'inline', marginRight: 4 }} />
                {result.successful}
              </div>
              <div className="batch-stat-label">Successful</div>
            </div>
            <div className="batch-stat" style={{ borderColor: 'var(--color-danger)' }}>
              <div className="batch-stat-value" style={{ color: 'var(--color-danger)' }}>
                <XCircle size={18} style={{ display: 'inline', marginRight: 4 }} />
                {result.failed}
              </div>
              <div className="batch-stat-label">Failed</div>
            </div>
            <div className="batch-stat" style={{ borderColor: 'var(--color-warning)' }}>
              <div className="batch-stat-value" style={{ color: 'var(--color-warning)' }}>
                <AlertTriangle size={18} style={{ display: 'inline', marginRight: 4 }} />
                {result.escalated}
              </div>
              <div className="batch-stat-label">Escalated</div>
            </div>
            <div className="batch-stat">
              <div className="batch-stat-value">₹{formatINR(result.amount_at_risk)}</div>
              <div className="batch-stat-label">Amount at Risk</div>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn--primary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
