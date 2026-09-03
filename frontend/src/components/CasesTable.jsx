import React from 'react';
import { RISKS, TERMINAL_STATES } from '../constants';
import { money, pretty } from '../utils/format';
import { Badge } from './Badge';
import { RiskBadge } from './RiskBadge';

export function CasesTable({
  cases, filtered, live, booting, freshness,
  search, setSearch, riskFilter, setRiskFilter,
  loading, inFlight, execute, viewCase,
}) {
  return (
    <section className="panel cases-panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Recovery queue</div>
          <h2>Payment recovery cases</h2>
          <p>{live ? cases.length + ' cases loaded from backend' : 'Backend offline — press Retry Connection for live data'} · showing {filtered.length} · {freshness}</p>
        </div>
        <div className="panel-tools">
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search cases…"
            aria-label="Search cases by customer, payment ID or failure reason"
          />
          <div className="risk-filters" role="group" aria-label="Filter cases by risk level">
            {RISKS.map(r => (
              <button
                key={r}
                type="button"
                className={`filter-btn ${riskFilter === r ? 'active' : ''}`}
                onClick={() => setRiskFilter(r)}
                aria-pressed={riskFilter === r}
              >
                {r === 'all' ? 'All risks' : pretty(r)}
              </button>
            ))}
          </div>
          <span className="test-chip">RAZORPAY TEST MODE</span>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Case</th>
              <th>Customer</th>
              <th>Payment</th>
              <th>Amount</th>
              <th>Risk</th>
              <th>Next retry</th>
              <th>Diagnosis</th>
              <th>AI Action</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {!live && !booting ? (
              <tr>
                <td colSpan={10}>
                  <div className="empty-state">
                    Backend offline — no live recovery data is shown. Press <strong>Retry Connection</strong> above, or start the backend with <code>uvicorn app.main:app --reload</code>.
                  </div>
                </td>
              </tr>
            ) : filtered.map(item => {
              const itemStatus = String(item.status || item.recovery_status || '').toLowerCase();
              const isTerm = TERMINAL_STATES.includes(itemStatus);
              return (
                <tr key={item.id}>
                  <td><strong>#{item.id}</strong></td>
                  <td>{item.customer?.name || item.customer_name || item.payment?.customer_name || 'Customer'}</td>
                  <td className="muted">{item.payment_id}</td>
                  <td className="amount">{money(item.amount ?? item.payment?.amount)}</td>
                  <td><RiskBadge risk={item.risk_level} /></td>
                  <td className="muted">{item.next_retry_at ? new Date(item.next_retry_at).toLocaleString() : '—'}</td>
                  <td className="diagnosis">{item.failure_reason || item.payment?.failure_reason || 'Payment failure detected'}</td>
                  <td>{pretty(item.recommended_action)}</td>
                  <td><Badge status={item.status} /></td>
                  <td>
                    <div className="row-actions">
                      {live && !isTerm && (
                        <button className={`execute-btn ${loading ? 'is-busy' : ''}`} disabled={loading} onClick={() => execute(item)}>
                          {loading && inFlight[item.id] ? 'Executing…' : 'Execute'}
                        </button>
                      )}
                      <button className="details-btn" onClick={() => viewCase(item)}>Details</button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {filtered.length === 0 && <div className="empty-state">No recovery cases match your search.</div>}
      </div>
    </section>
  );
}
