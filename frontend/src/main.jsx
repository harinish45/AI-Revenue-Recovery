import React from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';
import './enhancements.css';

import { useNotices } from './hooks/useNotices';
import { useDashboardData } from './hooks/useDashboardData';
import { useCaseExecution } from './hooks/useCaseExecution';
import { useBatchRecovery } from './hooks/useBatchRecovery';
import { useAuditTrail } from './hooks/useAuditTrail';
import { useClipboard } from './hooks/useClipboard';
import { useShortcuts } from './hooks/useShortcuts';

import { ErrorBoundary } from './components/ErrorBoundary';
import { TopBar } from './components/TopBar';
import { NoticeList } from './components/NoticeList';
import { MetricsRow } from './components/MetricsRow';
import { CasesTable } from './components/CasesTable';
import { ArchFlow } from './components/ArchFlow';
import { BatchResultModal } from './components/BatchResultModal';
import { CaseDetailModal } from './components/CaseDetailModal';
import { AuditDrawer } from './components/AuditDrawer';
import { ShortcutsModal } from './components/ShortcutsModal';

/* No demo fallback data: when the backend is unreachable the UI shows honest
   zeros and an offline state. All live data flows through api methods in ./api.js */

/* ---------- app ---------- */
function App() {
  const [selected, setSelected] = React.useState(null);
  const [search, setSearch] = React.useState('');
  const [riskFilter, setRiskFilter] = React.useState('all');

  const { notices, pushNotice, dismissNotice } = useNotices();
  const dashboard = useDashboardData(pushNotice);
  const { summary, cases, audit, setAudit, loading, setLoading, booting, live, lastUpdated, refresh, runAction, seed } = dashboard;

  const execution = useCaseExecution({ refresh, pushNotice, runAction, setSelected, setLoading });
  const { inFlight, failureArmed, setFailureArmed, execute, arm } = execution;

  const batchRecovery = useBatchRecovery({ cases, refresh, pushNotice, setLoading });
  const { batchResult, setBatchResult, progress, batch } = batchRecovery;

  const auditTrail = useAuditTrail({ audit, setAudit, pushNotice });
  const { auditOpen, setAuditOpen, openAuditDrawer, sealStatus, verifySeal, exportAudit } = auditTrail;

  const { copied, copyToClipboard } = useClipboard(pushNotice);
  const { shortcutsOpen, setShortcutsOpen } = useShortcuts();

  const reset = () => dashboard.reset(() => {
    setFailureArmed(false);
    setBatchResult(null);
  });

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
      <TopBar live={live} loading={loading} refresh={refresh} seed={seed} reset={reset} openShortcuts={() => setShortcutsOpen(true)} />

      <main>
        <NoticeList notices={notices} dismissNotice={dismissNotice} />

        <MetricsRow summary={summary} booting={booting} healthScore={healthScore} />

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

        <CasesTable
          cases={cases} filtered={filtered} live={live} booting={booting} freshness={freshness}
          search={search} setSearch={setSearch} riskFilter={riskFilter} setRiskFilter={setRiskFilter}
          loading={loading} inFlight={inFlight} execute={execute} setSelected={setSelected}
        />

        <ArchFlow />
      </main>

      <BatchResultModal batchResult={batchResult} progress={progress} onClose={() => setBatchResult(null)} />

      <CaseDetailModal
        selected={selected} cases={cases} audit={audit}
        copied={copied} copyToClipboard={copyToClipboard} onClose={() => setSelected(null)}
      />

      <AuditDrawer
        auditOpen={auditOpen} onClose={() => setAuditOpen(false)} audit={audit}
        exportAudit={exportAudit} verifySeal={verifySeal} sealStatus={sealStatus}
      />

      <ShortcutsModal shortcutsOpen={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
    </div>
  );
}

createRoot(document.getElementById('root')).render(<ErrorBoundary><App /></ErrorBoundary>);
