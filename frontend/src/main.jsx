import React from 'react';
import { createRoot } from 'react-dom/client';
import { api } from './api';
import './styles.css';
import './enhancements.css';

const demoSummary = { total_payments: 100, total_at_risk: 45000.5, total_recovered: 12000, recovery_rate_percent: 26.67, open_cases: 15, escalated_cases: 3 };
const money = (value = 0) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);
const pretty = (value = '') => String(value).replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
const demoCases = [
  { id: 1, payment_id: 'pay_demo_001', status: 'OPEN', retry_count: 0, diagnosis: 'Gateway timeout; customer has prior successful payments.', recommended_action: 'SEND_RETRY_LINK', payment: { amount: 2499, customer_name: 'Arjun Kumar', failure_reason: 'Gateway timeout' } },
  { id: 2, payment_id: 'pay_demo_014', status: 'OPEN', retry_count: 0, diagnosis: 'Issuer decline; safer to request a fresh payment authorization.', recommended_action: 'SEND_RETRY_LINK', payment: { amount: 1999, customer_name: 'Meera Iyer', failure_reason: 'Issuer decline' } },
  { id: 3, payment_id: 'pay_demo_021', status: 'RECOVERED', retry_count: 1, diagnosis: 'Transient gateway issue recovered within policy.', recommended_action: 'SEND_RETRY_LINK', payment: { amount: 4299, customer_name: 'Rohit Sharma', failure_reason: 'Gateway timeout' } },
];

function Badge({ status }) { const s = String(status || '').toLowerCase(); return <span className={`status-badge ${s}`}>{pretty(status)}</span>; }
function Metric({ label, value }) { return <div className="metric-card"><div className="metric-label">{label}</div><div className="metric-value">{value}</div></div>; }

function App() {
  const [summary, setSummary] = React.useState(demoSummary);
  const [cases, setCases] = React.useState(demoCases);
  const [audit, setAudit] = React.useState([]);
  const [loading, setLoading] = React.useState(false);
  const [live, setLive] = React.useState(false);
  const [failureArmed, setFailureArmed] = React.useState(false);
  const [auditOpen, setAuditOpen] = React.useState(false);
  const [selected, setSelected] = React.useState(null);
  const [notice, setNotice] = React.useState(null);

  const refresh = React.useCallback(async () => {
    try {
      const [s, c, a] = await Promise.all([api.getDashboard(), api.getCases(), api.getAudit()]);
      setSummary(s); setCases(c.items || []); setAudit(a.items || []); setLive(true);
    } catch { setLive(false); }
  }, []);
  React.useEffect(() => { refresh(); }, [refresh]);

  const action = async (fn, successText) => {
    setLoading(true); setNotice(null);
    try { const result = await fn(); setNotice({ type: 'success', text: successText || result?.message || 'Action completed.' }); await refresh(); return result; }
    catch (e) { setNotice({ type: 'error', text: e.message }); }
    finally { setLoading(false); }
  };

  const execute = async (item) => {
    setLoading(true); setNotice(null);
    try {
      const result = await api.executeRecovery(item.id);
      setSelected(null);
      setNotice({ type: result.status === 'ESCALATED' ? 'error' : 'success', text: result.status === 'ESCALATED' ? 'Escalated to Human Review due to gateway failure.' : `${pretty(result.action)} completed — ${money(result.amount_recovered)} recovered.` });
      await refresh();
    } catch (e) { setNotice({ type: 'error', text: e.message }); }
    finally { setLoading(false); }
  };

  const seed = () => action(api.seedDemo, '100 synthetic payments seeded successfully.');
  const reset = () => action(api.resetDemo, 'Demo database reset complete.');
  const batch = () => action(api.runRecoveryBatch, 'Batch recovery completed. Metrics refreshed.');
  const armFailure = async () => { const result = await action(api.simulateFailure, 'Failure simulation armed. Next execution will escalate.'); if (result) setFailureArmed(true); };

  return <div className="app-shell">
    <header className="topbar"><div><div className="eyebrow">Razorpay Hackathon · Track 03</div><h1>RecoverAI <span>— Autonomous Revenue Recovery</span></h1><p className="subtitle">Detect → Diagnose → Decide → Recover → Audit</p></div><div className="top-actions"><span className={`connection-state ${live ? 'online' : 'demo'}`}><span />{live ? 'Backend connected' : 'Demo fallback'}</span><button className="ghost-btn" disabled={loading} onClick={seed}>Seed Data</button><button className="ghost-btn" disabled={loading} onClick={reset}>Reset</button></div></header>
    <main>
      {notice && <div className={`notice ${notice.type}`}><strong>{notice.type === 'error' ? 'Recovery stopped' : 'Success'}</strong><span>{notice.text}</span><button onClick={() => setNotice(null)}>×</button></div>}
      <section className="metrics-grid"><Metric label="Total at risk" value={money(summary.total_at_risk)} /><Metric label="Total recovered" value={money(summary.total_recovered)} /><Metric label="Recovery rate" value={`${summary.recovery_rate_percent ?? 0}%`} /><Metric label="Open cases" value={summary.open_cases ?? 0} /><Metric label="Escalated cases" value={summary.escalated_cases ?? 0} /></section>
      <section className="action-center panel"><div><div className="eyebrow">Action center</div><h2>Close the recovery loop</h2><p>Every money action is bounded by the backend policy engine and recorded in the audit trail.</p></div><div className="action-buttons"><button className="primary-btn" disabled={loading} onClick={batch}>{loading ? 'Processing…' : 'Run Batch Recovery'}</button><button className={`failure-btn ${failureArmed ? 'armed' : ''}`} disabled={loading || failureArmed} onClick={armFailure}>{failureArmed ? 'Failure Armed — Next Execute Will Escalate' : 'Arm Failure Simulation'}</button><button className="audit-btn" onClick={() => setAuditOpen(true)}>Open Audit Trail</button></div></section>
      <section className="panel cases-panel"><div className="panel-header"><div><div className="eyebrow">Recovery queue</div><h2>Payment recovery cases</h2><p>Open cases are eligible for bounded recovery actions.</p></div><span className="test-chip">RAZORPAY TEST MODE</span></div><div className="table-wrap"><table><thead><tr><th>Case</th><th>Customer</th><th>Payment</th><th>Amount</th><th>Diagnosis</th><th>AI Action</th><th>Status</th><th /></tr></thead><tbody>{cases.map((item) => <tr key={item.id}><td><strong>#{item.id}</strong></td><td>{item.customer?.name || item.payment?.customer_name || 'Customer'}</td><td className="muted">{item.payment_id}</td><td className="amount">{money(item.amount ?? item.payment?.amount)}</td><td className="diagnosis">{item.diagnosis || item.payment?.failure_reason || 'Payment failure detected'}</td><td>{pretty(item.recommended_action)}</td><td><Badge status={item.status} /></td><td>{String(item.status).toUpperCase() === 'OPEN' ? <button className="execute-btn" disabled={loading} onClick={() => execute(item)}>Execute</button> : <button className="details-btn" onClick={() => setSelected(item)}>Details</button>}</td></tr>)}</tbody></table></div></section>
      <section className="pitch-proof"><div><strong>AI recommendation</strong><span>LLM proposes the action.</span></div><b>→</b><div><strong>Policy engine</strong><span>Backend gates the action.</span></div><b>→</b><div><strong>Razorpay Test Mode</strong><span>Bounded execution.</span></div><b>→</b><div><strong>Audit trail</strong><span>Every decision is explainable.</span></div></section>
    </main>
    {selected && <div className="modal-backdrop" onMouseDown={() => setSelected(null)}><div className="case-modal" onMouseDown={(e) => e.stopPropagation()}><div className="modal-header"><div><div className="eyebrow">Recovery case #{selected.id}</div><h2>{selected.payment?.customer_name || selected.customer?.name}</h2></div><button className="close-btn" onClick={() => setSelected(null)}>×</button></div><div className="case-detail"><div><span>Amount</span><strong>{money(selected.amount ?? selected.payment?.amount)}</strong></div><div><span>Status</span><Badge status={selected.status} /></div><div><span>Retry count</span><strong>{selected.retry_count}</strong></div></div><h3>Diagnosis</h3><p>{selected.diagnosis || 'Payment failure requires recovery review.'}</p><h3>Recommended action</h3><p>{pretty(selected.recommended_action)}</p></div></div>}
    {auditOpen && <div className="drawer-backdrop" onMouseDown={() => setAuditOpen(false)}><aside className="audit-drawer" onMouseDown={(e) => e.stopPropagation()}><div className="drawer-header"><div><div className="eyebrow">Compliance proof</div><h2>Audit Trail</h2></div><button className="close-btn" onClick={() => setAuditOpen(false)}>×</button></div><p>Raw backend events proving diagnosis, policy gating and execution.</p><div className="json-list">{audit.length ? audit.map((event) => <pre key={event.id}>{JSON.stringify(event, null, 2)}</pre>) : <pre>{JSON.stringify({ event_type: 'DEMO_AUDIT', details: { message: 'Seed and execute a case to populate live audit events.' } }, null, 2)}</pre>}</div></aside></div>}
  </div>;
}
createRoot(document.getElementById('root')).render(<App />);
