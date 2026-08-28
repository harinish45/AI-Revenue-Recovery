import React from 'react';
import { createRoot } from 'react-dom/client';
import { api } from './api';
import './styles.css';
import './enhancements.css';

/* ---------- helpers ---------- */
const money = v => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(Number(v) || 0);
const pretty = v => String(v ?? '').replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase());

/* No demo fallback data: when the backend is unreachable the UI shows honest
   zeros and an offline state. All live data flows through api methods in ./api.js */

const RISKS = ['all', 'LOW', 'MEDIUM', 'HIGH'];
const TERMINAL_STATES = new Set(['recovered', 'blocked', 'needs_human_review', 'skipped']);

/* ---------- small components ---------- */
function Badge({ status }) {
  const normalized = String(status || '').toLowerCase().replaceAll('_', ' ');
  const human = normalized === 'needs human review' || normalized === 'blocked';
  const awaiting = normalized === 'awaiting payment';
  return (
    <span className={`status-badge ${human ? 'needs-human-review' : String(status || '').toLowerCase()}`}>
      {human ? 'ESCALATED TO HUMAN' : awaiting ? 'AWAITING PAYMENT' : pretty(status)}
    </span>
  );
}

function RiskBadge({ risk }) {
  const r = String(risk || '').toUpperCase();
  const cls = r === 'HIGH' ? 'risk-high' : r === 'MEDIUM' ? 'risk-medium' : r === 'LOW' ? 'risk-low' : 'risk-unknown';
  return <span className={`risk-badge ${cls}`}>{r || 'UNKNOWN'}</span>;
}

function Metric({ label, value }) {
  const [shown, setShown] = React.useState(0);
  React.useEffect(() => {
    const target = Number(value) || 0; const started = performance.now(); let frame;
    const tick = now => { const progress = Math.min(1, (now - started) / 800); setShown(target * (1 - Math.pow(1 - progress, 3))); if (progress < 1) frame = requestAnimationFrame(tick); };
    frame = requestAnimationFrame(tick); return () => cancelAnimationFrame(frame);
  }, [value]);
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{label === 'Recovery rate' ? `${shown.toFixed(1)}%` : label.includes('cases') ? Math.round(shown) : money(shown)}</div>
    </div>
  );
}

class ErrorBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <div className="error-state"><h2>RecoverAI needs a refresh</h2><p>The interface hit an unexpected data-shape error. No money action was executed.</p><button className="primary-btn" onClick={() => window.location.reload()}>Reload demo</button></div> : this.props.children; }
}

/* ---------- app ---------- */
function App() {
  const [summary, setSummary] = React.useState({ total_at_risk: 0, total_recovered: 0, recovery_rate_percent: 0, open_cases: 0, escalated_cases: 0 });
  const [cases, setCases] = React.useState([]);
  const [audit, setAudit] = React.useState([]);
  const [loading, setLoading] = React.useState(false);
  const [booting, setBooting] = React.useState(true);
  const [live, setLive] = React.useState(false);
  const [failureArmed, setFailureArmed] = React.useState(false);
  const [auditOpen, setAuditOpen] = React.useState(false);
  const [selected, setSelected] = React.useState(null);
  const [batchResult, setBatchResult] = React.useState(null);
  const [notices, setNotices] = React.useState([]);
  const [search, setSearch] = React.useState('');
  const [riskFilter, setRiskFilter] = React.useState('all');
  const [copied, setCopied] = React.useState(false);
  const [progress, setProgress] = React.useState(0);
  const [inFlight, setInFlight] = React.useState({});
  const [sealStatus, setSealStatus] = React.useState({});
  const [lastUpdated, setLastUpdated] = React.useState(null);
  const [shortcutsOpen, setShortcutsOpen] = React.useState(false);

  const pushNotice = notice => setNotices(previous => [...previous, { ...notice, id: `${Date.now()}-${Math.random()}` }].slice(-4));

  // Map backend dashboard fields onto the names this UI renders
  const mapSummary = s => ({
    ...s,
    total_at_risk: s.total_at_risk ?? s.revenue_at_risk ?? 0,
    total_recovered: s.total_recovered ?? s.recovered_amount ?? 0,
    recovery_rate_percent: s.recovery_rate_percent ?? s.recovery_rate ?? 0,
    open_cases: s.open_cases ?? 0,
    escalated_cases: s.escalated_cases ?? 0,
  });

  const refresh = React.useCallback(async () => {
    try {
      const [s, c, a] = await Promise.all([api.getDashboard(), api.getCases(), api.getAudit()]);
      setSummary(mapSummary(s));
      setCases(c.items || []);
      setAudit(a.items || []);
      setLive(true);
      setLastUpdated(new Date());
      return true;
    } catch {
      setLive(false);
      return false;
    } finally { setBooting(false); }
  }, []);

  React.useEffect(() => { refresh(); }, [refresh]);

  React.useEffect(() => {
    const onKeyDown = event => {
      const tag = event.target?.tagName;
      if (event.key === '?' && tag !== 'INPUT' && tag !== 'TEXTAREA') setShortcutsOpen(true);
      if (event.key === 'Escape') setShortcutsOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  // Generic action wrapper: loading state + success/error toast
  const action = async (fn, text, type = 'success') => {
    setLoading(true);
    try {
      const result = await fn();
      pushNotice({ type, text: text || result?.message || 'Action completed.' });
      await refresh();
      return result;
    } catch (e) {
      pushNotice({ type: 'error', text: e.message });
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async text => {
    try {
      if (navigator.clipboard && window.isSecureContext && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(String(text));
        setCopied(true);
        setTimeout(() => setCopied(false), 1800);
        return;
      }
      throw new Error('Clipboard API unavailable');
    } catch {
      // Fallback for non-secure contexts (HTTP)
      const ta = document.createElement('textarea');
      ta.value = String(text);
      ta.style.position = 'fixed';
      ta.style.top = '0';
      ta.style.left = '0';
      ta.style.opacity = '0';
      ta.setAttribute('readonly', '');
      document.body.appendChild(ta);
      ta.select();
      ta.setSelectionRange(0, 99999);
      try {
        const ok = document.execCommand('copy');
        if (ok) {
          setCopied(true);
          setTimeout(() => setCopied(false), 1800);
        } else {
          pushNotice({ type: 'warning', text: 'Copy failed.' });
        }
      } catch {
        pushNotice({ type: 'warning', text: 'Copy failed.' });
      }
      document.body.removeChild(ta);
    }
  };

  const openAuditDrawer = async () => {
    setAuditOpen(true);
    try {
      const a = await api.getAudit();
      setAudit(a.items || []);
    } catch {
      /* retain state on failure */
    }
  };

  const execute = async item => {
    const terminal = ['recovered', 'blocked', 'needs_human_review', 'skipped'];
    const statusStr = String(item.status || item.recovery_status || '').toLowerCase();
    if (terminal.includes(statusStr)) {
      pushNotice({ type: 'warning', text: `Case #${item.id} is already ${pretty(statusStr)}.` });
      return;
    }
    if (inFlight[item.id]) return;
    setInFlight(previous => ({ ...previous, [item.id]: true })); setLoading(true);
    try {
      const r = await api.executeRecovery(item.id);
      setSelected(null);
      const status = String(r.status || '').toLowerCase();
      if (status === 'awaiting_payment') {
        pushNotice({ type: 'info', text: 'Intervention sent. Revenue will be counted only after the provider confirms the payment.' });
      } else if (status === 'recovered') {
        pushNotice({ type: 'success', text: 'Provider confirmed the payment — ' + money(r.recovered_amount) + ' recovered.' });
      } else if (status === 'needs_human_review' || status.includes('human') || status.includes('escalat')) {
        setFailureArmed(false);
        pushNotice({ type: 'error', text: r.message || 'Escalated to Human Review.' });
      } else if (status === 'skipped') {
        pushNotice({ type: 'info', text: r.message || 'Smart-skipped: intervention cost exceeds recovery value.' });
      } else {
        pushNotice({ type: status === 'recovered' ? 'success' : 'warning', text: r.message || pretty(r.action || 'Recovery') + ' completed.' });
      }
      await refresh();
    } catch (e) {
      pushNotice({ type: 'error', text: e.message });
    } finally {
      setInFlight(previous => ({ ...previous, [item.id]: false })); setLoading(false);
    }
  };

  const seed = () => action(api.seedDemo, '100 synthetic payments seeded successfully.');
  const reset = async () => {
    setLoading(true);
    try {
      await api.resetDemo();
      setFailureArmed(false);
      setBatchResult(null);
      setCases([]);
      setAudit([]);
      setSummary(demoSummary);
      pushNotice({ type: 'success', text: 'Database reset. Re-seeding demo data...' });
      await api.seedDemo();
      await refresh();
    } catch (e) {
      pushNotice({ type: 'error', text: e.message });
    } finally {
      setLoading(false);
    }
  };
  const batch = async () => {
    const pendingCases = cases.filter(c => {
      const s = String(c.status || c.recovery_status || '').toLowerCase();
      return s === 'open' || s === 'pending';
    });
    if (pendingCases.length === 0) {
      pushNotice({ type: 'warning', text: 'No pending cases to recover.' });
      return;
    }
    setLoading(true); setProgress(8);
    const progressTimer = setInterval(() => setProgress(previous => Math.min(92, previous + 9)), 260);
    try {
      const r = await api.runRecoveryBatch();
      setBatchResult(r);
      clearInterval(progressTimer); setProgress(100);
      pushNotice({ type: 'success', text: 'Recovered ' + money(r.recovered_amount) + ' across ' + r.successful + ' successful cases.' });
      await refresh();
      return r;
    } catch (e) {
      clearInterval(progressTimer); setProgress(0); pushNotice({ type: 'error', text: e.message });
    } finally {
      setLoading(false); setTimeout(() => setProgress(0), 500);
    }
  };
  const arm = async () => {
    const r = await action(api.simulateFailure, 'Gateway failure detected. Safely escalated to human review.', 'warning');
    if (r) setFailureArmed(true);
  };

  const verifySeal = async id => {
    try {
      const result = await api.verifyAudit(id);
      setSealStatus(previous => ({ ...previous, [id]: result }));
    } catch (e) {
      pushNotice({ type: 'error', text: e.message });
    }
  };

  const exportAudit = () => {
    const rows = [['id', 'case_id', 'event_type', 'actor', 'result', 'timestamp']];
    audit.forEach(event => rows.push([event.id, event.case_id || '', event.event_type, event.actor || '', event.result || '', event.timestamp || '']));
    const csv = rows.map(row => row.map(value => `"${String(value ?? '').replaceAll('"', '""')}"`).join(',')).join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    const link = document.createElement('a'); link.href = url; link.download = 'recoverai-audit.csv'; link.click(); URL.revokeObjectURL(url);
  };

  // Search across id/payment/customer/status/failure fields AND filter by risk level
  const filtered = cases.filter(c =>
    (riskFilter === 'all' || String(c.risk_level || '').toUpperCase() === riskFilter) &&
    `${c.id} ${c.payment_id} ${c.payment?.customer_name || c.customer?.name || ''} ${c.status} ${c.failure_category || ''} ${c.failure_reason || ''}`
      .toLowerCase()
      .includes(search.toLowerCase())
  );
  const complianceAverage = cases.length
    ? cases.reduce((total, item) => total + Number(item.compliance_score ?? 100), 0) / cases.length
    : 100;
  const escalationPenalty = Math.min(100, Number(summary.escalated_cases || 0) * 5);
  const healthScore = Math.max(0, Math.min(100, Math.round(
    (Number(summary.recovery_rate_percent || 0) * 0.4) + (complianceAverage * 0.4) + ((100 - escalationPenalty) * 0.2),
  )));
  const freshness = lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'Waiting for backend';

  return (
    <div className="app-shell">
      <div className="test-banner">
        <span className="warning-dot">●</span>
        <strong>Razorpay Hackathon Sandbox</strong>
        <span>|</span>
        <strong>Test Mode Active</strong>
        <span>|</span>
        <span>Simulated Gateway</span>
      </div>

      <header className="topbar">
        <div>
          <div className="eyebrow">Razorpay Hackathon · Track 03</div>
          <h1>RecoverAI <span>— Autonomous Revenue Recovery</span></h1>
          <p className="subtitle">Detect → Diagnose → Decide → Recover → Audit</p>
        </div>
        <div className="top-actions">
          <span className={`connection-state ${live ? 'online' : 'demo'}`}><span />{live ? 'Backend connected' : 'Demo fallback'}</span>
          {!live && <button className="ghost-btn" disabled={loading} onClick={refresh} title="Retry API connection">Retry Connection</button>}
          <button className="ghost-btn shortcut-btn" onClick={() => setShortcutsOpen(true)} title="Keyboard shortcuts">? Shortcuts</button>
          <button className="ghost-btn" disabled={loading} onClick={seed}>Seed Data</button>
          <button className="ghost-btn" disabled={loading} onClick={reset}>Reset</button>
        </div>
      </header>

      <main>
        {/* Toast / notice */}
        {notices.map(notice => (
          <div key={notice.id} className={`notice ${notice.type}`} role="status">
            <strong>{notice.type === 'error' ? 'Escalation' : notice.type === 'warning' ? 'Warning' : 'Success'}</strong>
            <span>{notice.text}</span>
            <button onClick={() => setNotices(previous => previous.filter(item => item.id !== notice.id))} aria-label="Dismiss notification">×</button>
          </div>
        ))}

        {/* Dashboard metrics */}
        {booting && <div className="loading-skeleton" aria-label="Loading dashboard"><i /><i /><i /><i /><i /></div>}
        <section className={`metrics-grid ${booting ? 'is-loading' : ''}`} aria-label="Dashboard metrics">
          <Metric label="Total at risk" value={summary.total_at_risk} />
          <Metric label="Total recovered" value={summary.total_recovered} />
          <Metric label="Recovery rate" value={summary.recovery_rate_percent ?? 0} />
          <Metric label="Open cases" value={summary.open_cases ?? 0} />
          <Metric label="Escalated cases" value={summary.escalated_cases ?? 0} />
          <div className={`health-score-card ${healthScore >= 75 ? 'healthy' : healthScore >= 50 ? 'watch' : 'critical'}`}>
            <div className="metric-label">Recovery Health Score</div>
            <div className="health-score-value">{healthScore}<small>/100</small></div>
            <div className="health-score-bar"><span style={{ width: `${healthScore}%` }} /></div>
            <span>{healthScore >= 75 ? 'Healthy operating signal' : healthScore >= 50 ? 'Watch intervention quality' : 'Needs operator attention'}</span>
          </div>
        </section>

        {/* Action center */}
        <section className="action-center panel">
          <div>
            <div className="eyebrow">Action center</div>
            <h2>Close the recovery loop</h2>
            <p>Every money action is bounded by the backend policy engine and recorded in the audit trail.</p>
          </div>
          <div className="action-buttons">
            <button className={`primary-btn ${loading ? 'is-busy' : ''}`} disabled={loading || !live} onClick={batch}>
              {loading ? 'Processing…' : 'Run Batch Recovery'}
            </button>
            <button className={`failure-btn ${failureArmed ? 'armed' : ''}`} disabled={loading || failureArmed || !live} onClick={arm}>
              {failureArmed ? '⚠ Failure Armed — Next Execute Will Escalate' : '⚠ Arm Failure Simulation'}
            </button>
            <button className="audit-btn" onClick={openAuditDrawer}>View Compliance Audit</button>
            <a className="audit-btn" href="/" title="Open the full multilingual agent cockpit">Open Full Agent Cockpit</a>
          </div>
          {progress > 0 && <div className="batch-progress" aria-label={`Batch progress ${progress}%`}><span style={{ width: `${progress}%` }} /><small>{progress >= 100 ? 'Recovery complete' : `Agent processing ${progress}%`}</small></div>}
        </section>

        {/* Cases table with search + risk filters */}
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
                  <th>Compliance</th>
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
                    <td colSpan={11}>
                      <div className="empty-state">
                        Backend offline — no live recovery data is shown. Press <strong>Retry Connection</strong> above, or start the backend with <code>uvicorn app.main:app --reload</code>.
                      </div>
                    </td>
                  </tr>
                ) : filtered.map(item => {
                  const itemStatus = String(item.status || item.recovery_status || '').toLowerCase();
                  const isTerm = ['recovered', 'blocked', 'needs_human_review', 'skipped'].includes(itemStatus);
                  return (
                    <tr key={item.id}>
                      <td><strong>#{item.id}</strong></td>
                      <td>{item.customer?.name || item.customer_name || item.payment?.customer_name || 'Customer'}</td>
                      <td className="muted">{item.payment_id}</td>
                      <td className="amount">{money(item.amount ?? item.payment?.amount)}</td>
                      <td><RiskBadge risk={item.risk_level} /></td>
                      <td><span className={`status-badge ${Number(item.compliance_score) >= 80 ? 'recovered' : 'pending'}`}>{Math.round(item.compliance_score || 0)}% safe</span></td>
                      <td className="muted">{item.next_retry_at ? new Date(item.next_retry_at).toLocaleString() : '—'}</td>
                      <td className="diagnosis">{item.diagnosis || item.failure_reason || item.payment?.failure_reason || 'Payment failure detected'}</td>
                      <td>{pretty(item.recommended_action)}</td>
                      <td><Badge status={item.status} /></td>
                      <td>
                        {isTerm ? (
                          <button className="execute-btn" disabled style={{ opacity: 0.35, cursor: 'not-allowed' }}>Done</button>
                        ) : live ? (
                          <button className={`execute-btn ${loading ? 'is-busy' : ''}`} disabled={loading} onClick={() => execute(item)}>
                            {loading && inFlight[item.id] ? 'Executing…' : 'Execute'}
                          </button>
                        ) : (
                          <button className="details-btn" onClick={() => setSelected(item)}>Details</button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {filtered.length === 0 && <div className="empty-state">No recovery cases match your search.</div>}
          </div>
        </section>

        <section className="pitch-proof">
          <div><strong>AI recommendation</strong><span>LLM proposes the action.</span></div>
          <b>→</b>
          <div><strong>Policy engine</strong><span>Backend gates the action.</span></div>
          <b>→</b>
          <div><strong>Razorpay Test Mode</strong><span>Bounded execution.</span></div>
          <b>→</b>
          <div><strong>Audit trail</strong><span>Every decision is explainable.</span></div>
        </section>
      </main>

      {/* Batch result modal */}
      {batchResult && (
        <div className="modal-backdrop" onMouseDown={() => setBatchResult(null)}>
          <div className={`case-modal batch-modal ${progress === 100 ? 'complete' : ''}`} onMouseDown={e => e.stopPropagation()} role="dialog" aria-label="Batch recovery result">
            <div className="modal-header">
              <div>
                <div className="eyebrow">Batch recovery result</div>
                <h2>Revenue recovery completed</h2>
              </div>
              <button className="close-btn" onClick={() => setBatchResult(null)} aria-label="Close">×</button>
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
      )}

      {/* Case detail drawer */}
      {selected && (
        <div className="modal-backdrop" onMouseDown={() => setSelected(null)}>
          <div className="case-modal" onMouseDown={e => e.stopPropagation()} role="dialog" aria-label={'Case detail ' + selected.id}>
            <div className="modal-header">
              <div>
                <div className="eyebrow">Recovery case #{selected.id}</div>
                <h2>{selected.payment?.customer_name || selected.customer?.name || selected.customer_name || 'Customer'}</h2>
              </div>
              <button className="close-btn" onClick={() => setSelected(null)} aria-label="Close">×</button>
            </div>

            <div className="case-detail">
              <div><span>Amount</span><strong>{money(selected.amount ?? selected.payment?.amount)}</strong></div>
              <div><span>Status</span><Badge status={selected.status} /></div>
              <div><span>Risk level</span><RiskBadge risk={selected.risk_level} /></div>
              <div><span>Retry count</span><strong>{selected.retry_count}</strong></div>
              <div><span>Compliance</span><strong>{Math.round(selected.compliance_score || 0)}% policy-safe</strong></div>
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
            <p>{selected.diagnosis || 'Payment failure requires recovery review.'}</p>
            <h3>Recommended action</h3>
            <p>{pretty(selected.recommended_action)}</p>
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
      )}

      {/* Audit trail drawer */}
      {auditOpen && (
        <div className="drawer-backdrop" onMouseDown={() => setAuditOpen(false)}>
          <aside className="audit-drawer" onMouseDown={e => e.stopPropagation()} aria-label="Compliance audit trail">
            <div className="drawer-header">
              <div>
                <div className="eyebrow">Compliance proof</div>
                <h2>Audit Trail</h2>
              </div>
              <button className="ghost-btn" onClick={exportAudit}>Export CSV</button>
              <button className="close-btn" onClick={() => setAuditOpen(false)} aria-label="Close">×</button>
            </div>
            <p>Compliance events from the backend, including diagnosis, policy gating and execution.</p>
            <div className="json-list">
              {audit.length
                ? audit.map(event => <div key={event.id} className={`audit-event ${String(event.result).toLowerCase().includes('fail') || String(event.event_type).includes('ESCALAT') ? 'negative' : String(event.result).toLowerCase().includes('skip') ? 'warning' : 'positive'}`}><i /><div><strong>{pretty(event.event_type)}</strong><span>{event.actor || 'system'} · {event.result || 'recorded'} · {event.timestamp ? new Date(event.timestamp).toLocaleString() : 'just now'}</span><small>{event.reason || event.action || 'Recorded compliance event'}</small><button className="details-btn" onClick={() => verifySeal(event.id)}>🔒 Verify seal</button>{sealStatus[event.id] && <em>{sealStatus[event.id].chain_verified ? 'Chain verified' : 'Chain invalid'} · {sealStatus[event.id].event_hash.slice(0, 16)}…</em>}</div></div>)
                : <div className="empty-state">No audit events yet. Seed and execute a case to populate live compliance events.</div>}
            </div>
          </aside>
        </div>
      )}

      {shortcutsOpen && (
        <div className="modal-backdrop" onMouseDown={() => setShortcutsOpen(false)}>
          <div className="case-modal shortcuts-modal" onMouseDown={event => event.stopPropagation()} role="dialog" aria-label="Keyboard shortcuts">
            <div className="modal-header"><div><div className="eyebrow">Operator controls</div><h2>Keyboard shortcuts</h2></div><button className="close-btn" onClick={() => setShortcutsOpen(false)} aria-label="Close">×</button></div>
            <div className="shortcut-list"><div><kbd>?</kbd><span>Open this help panel</span></div><div><kbd>Esc</kbd><span>Close any open panel</span></div><div><kbd>Ctrl / ⌘ K</kbd><span>Open the full agent cockpit</span></div></div>
            <p className="modal-footnote">Shortcuts never execute a money action. Recovery actions remain behind explicit buttons and backend policy gates.</p>
          </div>
        </div>
      )}
    </div>
  );
}

createRoot(document.getElementById('root')).render(<ErrorBoundary><App /></ErrorBoundary>);
