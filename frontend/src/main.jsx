import React from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const metrics = [
  { label: 'Revenue at risk', value: '₹18,750', note: '+12.4% vs. yesterday', tone: 'warning' },
  { label: 'Recovered revenue', value: '₹7,250', note: '38.7% recovery rate', tone: 'success' },
  { label: 'Failed payments', value: '20', note: 'from 100 transactions', tone: 'neutral' },
  { label: 'Escalated', value: '3', note: 'needs merchant review', tone: 'danger' },
];

const cases = [
  {
    id: 'RC-001', customer: 'Arjun Kumar', payment: 'pay_demo_001', amount: '₹2,499',
    reason: 'Gateway timeout', risk: 'High', action: 'Retry payment', status: 'Ready',
  },
  {
    id: 'RC-002', customer: 'Meera Iyer', payment: 'pay_demo_014', amount: '₹1,999',
    reason: 'Issuer decline', risk: 'Medium', action: 'Payment link', status: 'Review',
  },
  {
    id: 'RC-003', customer: 'Rohit Sharma', payment: 'pay_demo_021', amount: '₹4,299',
    reason: 'Gateway timeout', risk: 'High', action: 'Retry payment', status: 'Recovered',
  },
  {
    id: 'RC-004', customer: 'Nandhini Raj', payment: 'pay_demo_031', amount: '₹999',
    reason: 'Authentication failed', risk: 'Low', action: 'Customer prompt', status: 'Escalated',
  },
];

function MetricCard({ label, value, note, tone }) {
  return (
    <section className={`metric-card ${tone}`}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      <div className="metric-note">{note}</div>
    </section>
  );
}

function StatusPill({ children, type }) {
  return <span className={`pill ${type}`}>{children}</span>;
}

function App() {
  const [active, setActive] = React.useState('Overview');

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">R</div>
          <div>
            <div className="brand-name">RecoverAI</div>
            <div className="brand-subtitle">Revenue recovery</div>
          </div>
        </div>

        <nav className="nav-list">
          {['Overview', 'Recovery queue', 'Audit trail', 'Policies'].map((item) => (
            <button
              key={item}
              className={`nav-item ${active === item ? 'active' : ''}`}
              onClick={() => setActive(item)}
            >
              <span className="nav-dot" />
              {item}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="test-mode">
            <span className="mode-dot" />
            Razorpay Test Mode
          </div>
          <div className="version">Pitch build · v0.1</div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <div className="eyebrow">Merchant control center</div>
            <h1>{active === 'Overview' ? 'Revenue recovery overview' : active}</h1>
          </div>
          <div className="topbar-actions">
            <button className="ghost-btn">Reset demo</button>
            <button className="primary-btn">Run recovery batch</button>
          </div>
        </header>

        {active === 'Overview' && (
          <>
            <section className="hero-banner">
              <div>
                <div className="hero-kicker">AI revenue recovery</div>
                <h2>Turn failed payments back into cash.</h2>
                <p>RecoverAI detects revenue at risk, selects a bounded intervention, executes safely, and explains every money action.</p>
              </div>
              <div className="hero-status">
                <span className="status-ring" />
                Agent operational
              </div>
            </section>

            <section className="metric-grid">
              {metrics.map((metric) => <MetricCard key={metric.label} {...metric} />)}
            </section>

            <section className="content-grid">
              <div className="panel large-panel">
                <div className="panel-header">
                  <div>
                    <h3>Recovery queue</h3>
                    <p>Prioritized cases requiring an action.</p>
                  </div>
                  <button className="text-btn">View all</button>
                </div>

                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Customer</th>
                        <th>Amount</th>
                        <th>Failure</th>
                        <th>Risk</th>
                        <th>AI action</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cases.map((item) => (
                        <tr key={item.id}>
                          <td>
                            <div className="customer-cell">
                              <div className="avatar">{item.customer.split(' ').map((x) => x[0]).join('').slice(0, 2)}</div>
                              <div>
                                <strong>{item.customer}</strong>
                                <span>{item.id}</span>
                              </div>
                            </div>
                          </td>
                          <td className="amount">{item.amount}</td>
                          <td>{item.reason}</td>
                          <td><StatusPill type={item.risk.toLowerCase()}>{item.risk}</StatusPill></td>
                          <td>{item.action}</td>
                          <td><StatusPill type={item.status.toLowerCase().replace(' ', '-')}>{item.status}</StatusPill></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="panel agent-panel">
                <div className="panel-header">
                  <div>
                    <h3>Latest agent decision</h3>
                    <p>RC-001 · ₹2,499 at risk</p>
                  </div>
                  <StatusPill type="high">HIGH</StatusPill>
                </div>

                <div className="decision-card">
                  <div className="decision-label">Decision</div>
                  <div className="decision-title">Retry payment</div>
                  <p>Customer has 8 successful historical payments, only 1 previous failure, and the case is below the retry limit.</p>

                  <div className="checks">
                    <div><span className="check">✓</span> Test mode only</div>
                    <div><span className="check">✓</span> Retry count 0 / 2</div>
                    <div><span className="check">✓</span> Amount below policy limit</div>
                  </div>
                </div>

                <button className="recover-btn">Review recovery action</button>
              </div>
            </section>

            <section className="bottom-grid">
              <div className="panel">
                <div className="panel-header">
                  <div>
                    <h3>Recovery performance</h3>
                    <p>Current demo batch</p>
                  </div>
                  <div className="trend">↑ 8.2%</div>
                </div>
                <div className="bar-chart">
                  {[42, 60, 52, 72, 66, 84, 78, 92].map((height, index) => (
                    <div className="bar-group" key={index}>
                      <div className="bar" style={{ height: `${height}%` }} />
                      <span>W{index + 1}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="panel audit-panel">
                <div className="panel-header">
                  <div>
                    <h3>Recent audit activity</h3>
                    <p>Every financial action is logged.</p>
                  </div>
                  <button className="text-btn">Open audit trail</button>
                </div>
                <div className="audit-list">
                  <div className="audit-row"><span className="audit-time">18:01:05</span><span>Recovery succeeded</span><strong>₹2,499</strong></div>
                  <div className="audit-row"><span className="audit-time">18:01:04</span><span>Policy validation passed</span><strong>RC-001</strong></div>
                  <div className="audit-row"><span className="audit-time">18:01:03</span><span>Strategy selected</span><strong>Retry</strong></div>
                  <div className="audit-row"><span className="audit-time">18:01:02</span><span>Revenue risk calculated</span><strong>₹2,499</strong></div>
                </div>
              </div>
            </section>
          </>
        )}

        {active !== 'Overview' && (
          <section className="panel placeholder-panel">
            <div className="placeholder-icon">◎</div>
            <h2>{active}</h2>
            <p>This module is scaffolded for live backend integration. The shared API contract is already defined in <code>docs/api-contract.md</code>.</p>
          </section>
        )}
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
