import React from 'react';
import { pretty } from '../utils/format';

export function AuditDrawer({ auditOpen, onClose, audit, exportAudit, verifySeal, sealStatus }) {
  if (!auditOpen) return null;
  return (
    <div className="drawer-backdrop" onMouseDown={onClose}>
      <aside className="audit-drawer" onMouseDown={e => e.stopPropagation()} aria-label="Compliance audit trail">
        <div className="drawer-header">
          <div>
            <div className="eyebrow">Compliance proof</div>
            <h2>Audit Trail</h2>
          </div>
          <button className="ghost-btn" onClick={exportAudit}>Export CSV</button>
          <button className="close-btn" onClick={onClose} aria-label="Close">×</button>
        </div>
        <p>Compliance events from the backend, including diagnosis, policy gating and execution.</p>
        <div className="json-list">
          {audit.length
            ? audit.map(event => (
              <div key={event.id} className={`audit-event ${String(event.result).toLowerCase().includes('fail') || String(event.event_type).includes('ESCALAT') ? 'negative' : String(event.result).toLowerCase().includes('skip') ? 'warning' : 'positive'}`}>
                <i />
                <div>
                  <strong>{pretty(event.event_type)}</strong>
                  <span>{event.actor || 'system'} · {event.result || 'recorded'} · {event.timestamp ? new Date(event.timestamp).toLocaleString() : 'just now'}</span>
                  <small>{event.reason || event.action || 'Recorded compliance event'}</small>
                  <button className="details-btn" onClick={() => verifySeal(event.id)}>🔒 Verify seal</button>
                  {sealStatus[event.id] && <em>{sealStatus[event.id].chain_verified ? 'Chain verified' : 'Chain invalid'} · {sealStatus[event.id].event_hash.slice(0, 16)}…</em>}
                </div>
              </div>
            ))
            : <div className="empty-state">No audit events yet. Seed and execute a case to populate live compliance events.</div>}
        </div>
      </aside>
    </div>
  );
}
