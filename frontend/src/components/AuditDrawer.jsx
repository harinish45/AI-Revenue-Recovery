import React, { useEffect, useState } from 'react';
import { X, FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { api } from '../services/api';

const EVENT_TYPE_COLORS = {
  LLM_DIAGNOSIS: 'var(--color-accent)',
  POLICY_CHECK: 'var(--color-info)',
  EXECUTION_STARTED: 'var(--color-warning)',
  RAZORPAY_API_CALL: 'var(--color-purple)',
  EXECUTION_COMPLETE: 'var(--color-success)',
  RECOVERY_FAILED: 'var(--color-danger)',
  ESCALATED_TO_HUMAN: 'var(--color-danger)',
  POLICY_REJECTION: 'var(--color-danger)',
};

function AuditEvent({ log }) {
  const [expanded, setExpanded] = useState(false);
  const color = EVENT_TYPE_COLORS[log.event_type] || 'var(--color-text-muted)';

  const decisionClass = {
    APPROVED: 'approved',
    REJECTED: 'rejected',
    ESCALATED: 'escalated',
    SIMULATED: 'simulated',
    ESCALATE: 'escalated',
    HUMAN_REVIEW: 'escalated',
    FAILED: 'rejected',
    SUCCESS: 'approved',
    NEEDS_HUMAN_REVIEW: 'escalated',
  }[log.decision] || '';

  return (
    <div className="audit-event">
      <div
        className="audit-timeline-dot"
        style={{ background: color }}
      />
      <div className="audit-event-content">
        <div className="audit-event-header">
          <span className="audit-event-type" style={{ color }}>
            {log.event_type}
          </span>
          {log.actor && (
            <span className="audit-event-actor">{log.actor}</span>
          )}
          {log.decision && (
            <span className={`audit-event-decision audit-decision--${decisionClass}`}>
              {log.decision}
            </span>
          )}
          {log.case_id && (
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
              Case #{log.case_id}
            </span>
          )}
          <span className="audit-event-time">
            {new Date(log.timestamp).toLocaleTimeString('en-IN')}
          </span>
        </div>
        {log.result_summary && (
          <div className="audit-summary">{log.result_summary}</div>
        )}
        {log.details && Object.keys(log.details).length > 0 && (
          <button
            style={{ all: 'unset', cursor: 'pointer', fontSize: '11px', color: 'var(--color-text-muted)', marginTop: 4, display: 'flex', alignItems: 'center', gap: 4 }}
            onClick={() => setExpanded(p => !p)}
          >
            {expanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
            {expanded ? 'Hide details' : 'Show details'}
          </button>
        )}
        {expanded && log.details && (
          <div className="audit-details">
            {JSON.stringify(log.details, null, 2)}
          </div>
        )}
      </div>
    </div>
  );
}

export default function AuditDrawer({ onClose }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const data = await api.getAudit(500);
        setLogs(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const filtered = filter
    ? logs.filter(l => l.event_type === filter || l.actor?.includes(filter))
    : logs;

  const eventTypes = [...new Set(logs.map(l => l.event_type))];

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <div className="drawer" style={{ width: '640px' }} role="dialog" aria-modal="true">
        <div className="drawer-header">
          <div className="drawer-title">
            <FileText size={16} style={{ color: 'var(--color-accent)' }} />
            Compliance Audit Trail
          </div>
          <button className="btn btn--ghost btn--sm" onClick={onClose}>
            <X size={14} /> Close
          </button>
        </div>

        {/* Filter */}
        <div style={{ padding: 'var(--space-3) var(--space-6)', borderBottom: '1px solid var(--color-border)', display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
          <button
            className={`btn btn--sm ${filter === '' ? 'btn--primary' : 'btn--ghost'}`}
            onClick={() => setFilter('')}
          >
            All ({logs.length})
          </button>
          {eventTypes.map(et => (
            <button
              key={et}
              className={`btn btn--sm ${filter === et ? 'btn--primary' : 'btn--ghost'}`}
              onClick={() => setFilter(f => f === et ? '' : et)}
              style={{ fontSize: '11px' }}
            >
              {et.replace(/_/g, ' ')}
            </button>
          ))}
        </div>

        <div className="drawer-body">
          {loading && <div className="loading-container"><div className="spinner" /></div>}
          {!loading && filtered.length === 0 && (
            <div className="empty-state">
              <div className="empty-state-title">No Audit Events</div>
              <div className="empty-state-text">Seed data and run recoveries to generate audit events.</div>
            </div>
          )}
          {!loading && filtered.map(log => (
            <AuditEvent key={log.id} log={log} />
          ))}
        </div>
      </div>
    </>
  );
}
