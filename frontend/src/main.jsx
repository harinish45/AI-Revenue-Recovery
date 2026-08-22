import React from 'react';
import { createRoot } from 'react-dom/client';
import { api } from './api';
import './styles.css';
import './enhancements.css';

const demoSummary = { total_transactions: 100, total_revenue: 124500, failed_payments: 20, revenue_at_risk: 18750, recovered_amount: 7250, recovery_rate: 38.7, recovery_attempts: 15, successful_recoveries: 9, failed_recoveries: 6, escalated_cases: 3 };
const demoCases = [
  { id: 'RC-001', customer: { name: 'Arjun Kumar' }, payment_id: 'pay_demo_001', amount: 2499, currency: 'INR', failure_reason: 'Gateway timeout', risk_level: 'HIGH', recommended_action: 'RETRY_PAYMENT', status: 'READY', retry_count: 0, max_retries: 2 },
  { id: 'RC-002', customer: { name: 'Meera Iyer' }, payment_id: 'pay_demo_014', amount: 1999, currency: 'INR', failure_reason: 'Issuer decline', risk_level: 'MEDIUM', recommended_action: 'PAYMENT_LINK', status: 'REVIEW', retry_count: 0, max_retries: 2 },
  { id: 'RC-003', customer: { name: 'Rohit Sharma' }, payment_id: 'pay_demo_021', amount: 4299, currency: 'INR', failure_reason: 'Gateway timeout', risk_level: 'HIGH', recommended_action: 'RETRY_PAYMENT', status: 'RECOVERED', retry_count: 1, max_retries: 2, recovered_amount: 4299 },
  { id: 'RC-004', customer: { name: 'Nandhini Raj' }, payment_id: 'pay_demo_031', amount: 999, currency: 'INR', failure_reason: 'Authentication failed', risk_level: 'LOW', recommended_action: 'CUSTOMER_PROMPT', status: 'ESCALATED', retry_count: 2, max_retries: 2 },
];
const demoAudit = [
  { id: 'AUD-001', timestamp: '18:01:05', event_type: 'RECOVERY_SUCCEEDED', action: 'Recovery succeeded', result: '₹2,499', case_id: 'RC-001' },
  { id: 'AUD-002', timestamp: '18:01:04', event_type: 'POLICY_VALIDATED', action: 'Policy validation passed', result: 'RC-001', case_id: 'RC-001' },
  { id: 'AUD-003', timestamp: '18:01:03', event_type: 'STRATEGY_SELECTED', action: 'Strategy selected', result: 'Retry payment', case_id: 'RC-001' },
  { id: 'AUD-004', timestamp: '18:01:02', event_type: 'RISK_CALCULATED', action: 'Revenue risk calculated', result: '₹2,499', case_id: 'RC-001' },
];
const money = (value = 0) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);
const prettyAction = (value = '') => value.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
function StatusPill({ children, type = '' }) { return <span className={`pill ${String(type).toLowerCase().replaceAll('_', '-')}`}>{children}</span>; }
function MetricCard({ label, value, note, tone = '' }) { return <section className={`metric-card ${tone}`}><div className="metric-label">{label}</div><div className="metric-value">{value}</div><div className="metric-note">{note}</div></section>; }

function App() {
  const [active, setActive] = React.useState('Overview');
  const [summary, setSummary] = React.useState(demoSummary);
  const [cases, setCases] = React.useState(demoCases);
  const [audit, setAudit] = React.useState(demoAudit);
  const [selected, setSelected] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [notice, setNotice] = React.useState(null);
  const [search, setSearch] = React.useState('');

  const refresh = React.useCallback(async () => {
    setLoading(true);
    try {
      const [nextSummary, nextCases, nextAudit] = await Promise.all([api.getDashboard(), api.getCases('?page_size=50'), api.getAudit('?page_size=20')]);
      setSummary(nextSummary); setCases(nextCases.items || []); setAudit(nextAudit.items || []); setNotice({ type: 'success', text: 'Live backend data loaded.' });
    } catch (error) { setNotice({ type: 'warning', text: `Backend not connected — showing demo data. ${error.message}` }); }
    finally { setLoading(false); }
  }, []);
  React.useEffect(() => { refresh(); }, [refresh]);

  const runAction = async (label, action) => {
    setLoading(true); setNotice(null);
    try { const result = await action(); setNotice({ type: result?.status === 'FAILED' ? 'danger' : 'success', text: result?.message || `${label} completed.` }); await refresh(); }
    catch (error) { setNotice({ type: 'danger', text: error.message }); }
    finally { setLoading(false); }
  };
  const openCase = async (item) => {
    setSelected({ ...item, loading: true });
    try { setSelected(await api.getCase(item.id)); }
    catch { setSelected({ ...item, demo: true, decision: { decision: item.recommended_action, reason: 'Customer history indicates the case is within the configured recovery policy.', evidence: ['Previous successful payments', `Retry count ${item.retry_count}/${item.max_retries}`], policy_checks: ['Test mode only', 'Below retry limit', 'Amount within policy'] }, audit_events: demoAudit.filter((x) => x.case_id === item.id || item.id === 'RC-001') }); }
  };
  const filteredCases = cases.filter((item) => `${item.customer?.name || ''} ${item.id} ${item.failure_reason || ''}`.toLowerCase().includes(search.toLowerCase()));
  const metrics = [
    { label: 'Revenue at risk', value: money(summary.revenue_at_risk), note: `${summary.failed_payments || 0} failed payments`, tone: 'warning' },
    { label: 'Recovered revenue', value: money(summary.recovered_amount), note: `${summary.recovery_rate || 0}% recovery rate`, tone: 'success' },
    { label: 'Transactions', value: summary.total_transactions || 0, note: `${money(summary.total_revenue)} processed`, tone: '' },
    { label: 'Escalated', value: summary.escalated_cases || 0, note: 'needs merchant review', tone: 'danger' },
  ];
  const nav = ['Overview', 'Recovery queue', 'Audit trail', 'Policies'];

  return <div className="app-shell">
    <aside className="sidebar"><div className="brand-block"><div className="brand-mark">R</div><div><div className="brand-name">RecoverAI</div><div className="brand-subtitle">Revenue recovery</div></div></div><nav className="nav-list">{nav.map((item) => <button key={item} className={`nav-item ${active === item ? 'active' : ''}`} onClick={() => setActive(item)}><span className="nav-dot" />{item}</button>)}</nav><div className="sidebar-footer"><div className="test-mode"><span className="mode-dot" />Razorpay Test Mode</div><div className="version">Pitch build · v0.2</div></div></aside>
    <main className="main-content">
      <header className="topbar"><div><div className="eyebrow">Merchant control center</div><h1>{active === 'Overview' ? 'Revenue recovery overview' : active}</h1></div><div className="topbar-actions"><button className="ghost-btn" disabled={loading} onClick={() => runAction('Demo reset', api.resetDemo)}>Reset demo</button><button className="primary-btn" disabled={loading} onClick={() => runAction('Recovery batch', api.runRecoveryBatch)}>Run recovery batch</button></div></header>
      {notice && <div className={`notice ${notice.type}`}><span>{notice.type === 'success' ? '✓' : notice.type === 'danger' ? '!' : 'i'}</span>{notice.text}<button onClick={() => setNotice(null)}>×</button></div>}
      {active === 'Overview' && <><section className="hero-banner"><div><div className="hero-kicker">AI revenue recovery</div><h2>Turn failed payments back into cash.</h2><p>RecoverAI detects revenue at risk, selects a bounded intervention, executes safely, and explains every money action.</p></div><div className="hero-status"><span className="status-ring" />Agent operational</div></section><section className="metric-grid">{metrics.map((metric) => <MetricCard key={metric.label} {...metric} />)}</section><section className="content-grid"><div className="panel large-panel"><div className="panel-header"><div><h3>Recovery queue</h3><p>Prioritized cases requiring an action.</p></div><button className="text-btn" onClick={() => setActive('Recovery queue')}>View all</button></div><div className="queue-toolbar"><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search customer, case or failure..." /><span>{filteredCases.length} cases</span></div><div className="table-wrap"><table><thead><tr><th>Customer</th><th>Amount</th><th>Failure</th><th>Risk</th><th>AI action</th><th>Status</th></tr></thead><tbody>{filteredCases.map((item) => <tr key={item.id} onClick={() => openCase(item)} className="clickable-row"><td><div className="customer-cell"><div className="avatar">{(item.customer?.name || 'NA').split(' ').map((x) => x[0]).join('').slice(0, 2)}</div><div><strong>{item.customer?.name || 'Unknown'}</strong><span>{item.id}</span></div></div></td><td className="amount">{money(item.amount)}</td><td>{item.failure_reason}</td><td><StatusPill type={item.risk_level}>{item.risk_level}</StatusPill></td><td>{prettyAction(item.recommended_action)}</td><td><StatusPill type={item.status}>{prettyAction(item.status)}</StatusPill></td></tr>)}</tbody></table></div></div><div className="panel agent-panel"><div className="panel-header"><div><h3>Latest agent decision</h3><p>RC-001 · ₹2,499 at risk</p></div><StatusPill type="HIGH">HIGH</StatusPill></div><div className="decision-card"><div className="decision-label">Decision</div><div className="decision-title">Retry payment</div><p>Customer history and policy checks indicate this payment is eligible for one bounded recovery attempt.</p><div className="checks"><div><span className="check">✓</span>Test mode only</div><div><span className="check">✓</span>Retry count 0 / 2</div><div><span className="check">✓</span>Amount below policy limit</div></div></div><button className="recover-btn" onClick={() => openCase(cases[0])}>Review recovery action</button></div></section><section className="bottom-grid"><div className="panel"><div className="panel-header"><div><h3>Recovery performance</h3><p>Current batch · {summary.recovery_attempts || 0} attempts</p></div><div className="trend">{summary.recovery_rate || 0}%</div></div><div className="bar-chart">{[42,60,52,72,66,84,78,92].map((height, index) => <div className="bar-group" key={index}><div className="bar" style={{ height: `${height}%` }} /><span>W{index + 1}</span></div>)}</div></div><AuditPanel audit={audit} onOpen={() => setActive('Audit trail')} /></section></>}
      {active === 'Recovery queue' && <QueuePage cases={filteredCases} search={search} setSearch={setSearch} onOpen={openCase} />}
      {active === 'Audit trail' && <AuditPage audit={audit} />}
      {active === 'Policies' && <PolicyPage />}
    </main>
    {selected && <CaseModal item={selected} loading={loading} onClose={() => setSelected(null)} onExecute={() => runAction('Recovery action', () => api.executeRecovery(selected.id))} />}
  </div>;
}
function AuditPanel({ audit, onOpen }) { return <div className="panel audit-panel"><div className="panel-header"><div><h3>Recent audit activity</h3><p>Every financial action is logged.</p></div><button className="text-btn" onClick={onOpen}>Open audit trail</button></div><div className="audit-list">{(audit.length ? audit.slice(0, 5) : demoAudit).map((event) => <div className="audit-row" key={event.id}><span className="audit-time">{event.timestamp?.slice(11, 19) || event.timestamp}</span><span>{event.action || event.event_type}</span><strong>{event.result || event.case_id}</strong></div>)}</div></div>; }
function QueuePage({ cases, search, setSearch, onOpen }) { return <section className="panel page-panel"><div className="panel-header"><div><h3>Recovery queue</h3><p>Every eligible case is bounded by backend policy.</p></div><StatusPill type="READY">LIVE QUEUE</StatusPill></div><div className="queue-toolbar"><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search customer, case or failure..." /><span>{cases.length} visible</span></div><div className="table-wrap"><table><thead><tr><th>Case</th><th>Customer</th><th>Amount</th><th>Failure</th><th>Risk</th><th>Action</th><th>Status</th></tr></thead><tbody>{cases.map((item) => <tr key={item.id} onClick={() => onOpen(item)} className="clickable-row"><td>{item.id}</td><td>{item.customer?.name}</td><td className="amount">{money(item.amount)}</td><td>{item.failure_reason}</td><td><StatusPill type={item.risk_level}>{item.risk_level}</StatusPill></td><td>{prettyAction(item.recommended_action)}</td><td><StatusPill type={item.status}>{prettyAction(item.status)}</StatusPill></td></tr>)}</tbody></table></div></section>; }
function AuditPage({ audit }) { return <section className="panel page-panel"><div className="panel-header"><div><h3>Audit trail</h3><p>Event history for the recovery workflow.</p></div><StatusPill type="SUCCESS">LOGGING ON</StatusPill></div><div className="timeline">{(audit.length ? audit : demoAudit).map((event) => <div className="timeline-item" key={event.id}><div className="timeline-dot" /><div className="timeline-body"><div className="timeline-top"><strong>{event.action || event.event_type}</strong><span>{event.timestamp}</span></div><p>{event.reason || 'Recovery workflow event recorded by the backend.'}</p><div className="timeline-meta"><span>{event.case_id}</span><span>{event.result || event.action}</span></div></div></div>)}</div></section>; }
function PolicyPage() { return <section className="policy-grid"><div className="panel policy-card"><div className="panel-header"><div><h3>Automatic recovery guardrails</h3><p>These controls are enforced server-side.</p></div><StatusPill type="SUCCESS">ENFORCED</StatusPill></div><div className="policy-list"><div><span>Maximum retries</span><strong>2</strong></div><div><span>Test mode only</span><strong>ON</strong></div><div><span>Duplicate execution protection</span><strong>ON</strong></div><div><span>Human escalation</span><strong>ON</strong></div><div><span>Unknown failure handling</span><strong>ESCALATE</strong></div></div></div><div className="panel policy-card"><div className="panel-header"><div><h3>Agent authority</h3><p>LLM recommendations never bypass policy.</p></div></div><div className="authority-flow"><span>AI recommendation</span><b>→</b><span>Policy engine</span><b>→</b><span>Recovery executor</span><b>→</b><span>Razorpay Test Mode</span></div><div className="policy-note">The model recommends. The backend decides whether an action is permitted.</div></div></section>; }
function CaseModal({ item, loading, onClose, onExecute }) { const decision = item.decision || {}; const terminal = ['RECOVERED', 'FAILED', 'ESCALATED'].includes(item.status); return <div className="modal-backdrop" onMouseDown={onClose}><div className="case-modal" onMouseDown={(e) => e.stopPropagation()}><div className="modal-header"><div><div className="eyebrow">Recovery case</div><h2>{item.id}</h2></div><button className="close-btn" onClick={onClose}>×</button></div><div className="case-summary"><div><span>Customer</span><strong>{item.customer?.name}</strong></div><div><span>Amount at risk</span><strong>{money(item.amount)}</strong></div><div><span>Failure</span><strong>{item.failure_reason}</strong></div><div><span>Status</span><StatusPill type={item.status}>{prettyAction(item.status)}</StatusPill></div></div><div className="modal-grid"><div><div className="section-label">AI decision</div><div className="decision-card"><div className="decision-title">{prettyAction(decision.decision || item.recommended_action)}</div><p>{decision.reason || 'The recovery case is eligible for a bounded intervention based on available customer and payment history.'}</p>{decision.evidence && <div className="checks">{decision.evidence.map((x) => <div key={x}><span className="check">✓</span>{x}</div>)}</div>}</div></div><div><div className="section-label">Policy checks</div><div className="policy-mini">{(decision.policy_checks || ['Test mode only', `Retry count ${item.retry_count || 0}/${item.max_retries || 2}`, 'Amount within policy']).map((x) => <div key={x}><span className="check">✓</span>{x}</div>)}</div></div></div><div className="modal-footer"><span className="audit-safe">Every action is audited and bounded.</span>{!terminal && <button className="primary-btn" disabled={loading} onClick={onExecute}>{loading ? 'Executing…' : `Execute ${prettyAction(item.recommended_action)}`}</button>}{terminal && <button className="ghost-btn" onClick={onClose}>Close</button>}</div></div></div>; }

createRoot(document.getElementById('root')).render(<App />);
