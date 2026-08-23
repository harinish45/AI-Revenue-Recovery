import React, { useState, useEffect, useCallback, useRef } from 'react';
import './index.css';
import { api } from './services/api';
import SandboxBanner from './components/SandboxBanner';
import Navbar from './components/Navbar';
import MetricsGrid from './components/MetricsGrid';
import ActionCenter from './components/ActionCenter';
import CasesTable from './components/CasesTable';
import CaseDetailDrawer from './components/CaseDetailDrawer';
import AuditDrawer from './components/AuditDrawer';
import BatchResultModal from './components/BatchResultModal';
import Toast from './components/Toast';
import { AlertTriangle } from 'lucide-react';

function App() {
  const [dashboard, setDashboard] = useState(null);
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toasts, setToasts] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [showAudit, setShowAudit] = useState(false);
  const [batchResult, setBatchResult] = useState(null);
  const [failureArmed, setFailureArmed] = useState(false);
  const [activeAction, setActiveAction] = useState(null);
  const [providers, setProviders] = useState(null);
  const toastId = useRef(0);

  const addToast = useCallback((message, type = 'info') => {
    const id = ++toastId.current;
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 5000);
  }, []);

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const fetchDashboard = useCallback(async () => {
    try {
      const data = await api.getDashboard();
      setDashboard(data);
    } catch (err) {
      console.error('Dashboard fetch failed', err);
    }
  }, []);

  const fetchCases = useCallback(async () => {
    try {
      const data = await api.getCases();
      setCases(data);
    } catch (err) {
      console.error('Cases fetch failed', err);
    }
  }, []);

  const fetchFailureStatus = useCallback(async () => {
    try {
      const data = await api.getFailureStatus();
      setFailureArmed(data.failure_armed);
    } catch (err) {
      // non-critical
    }
  }, []);

  const fetchProviders = useCallback(async () => {
    try {
      const data = await api.getProviders();
      setProviders(data);
    } catch (err) {
      // non-critical
    }
  }, []);

  const refreshAll = useCallback(async () => {
    await Promise.all([fetchDashboard(), fetchCases(), fetchFailureStatus()]);
  }, [fetchDashboard, fetchCases, fetchFailureStatus]);

  // Initial load
  useEffect(() => {
    const init = async () => {
      setLoading(true);
      setError(null);
      try {
        await refreshAll();
        await fetchProviders();
      } catch (err) {
        setError(err?.error?.message || 'Failed to connect to RecoverAI backend');
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const timer = setInterval(refreshAll, 30000);
    return () => clearInterval(timer);
  }, [refreshAll]);

  const handleSeed = async () => {
    setActiveAction('seed');
    try {
      const result = await api.seedDemo();
      addToast(result.message, 'success');
      await refreshAll();
    } catch (err) {
      addToast(err?.error?.message || 'Seed failed', 'error');
    } finally {
      setActiveAction(null);
    }
  };

  const handleReset = async () => {
    setActiveAction('reset');
    try {
      const result = await api.resetDemo();
      addToast(result.message, 'info');
      setFailureArmed(false);
      setBatchResult(null);
      await refreshAll();
    } catch (err) {
      addToast(err?.error?.message || 'Reset failed', 'error');
    } finally {
      setActiveAction(null);
    }
  };

  const handleBatch = async () => {
    setActiveAction('batch');
    try {
      const result = await api.runBatch();
      setBatchResult(result);
      await refreshAll();
      addToast(
        `Recovered ₹${result.amount_recovered.toLocaleString('en-IN', { minimumFractionDigits: 2 })} across ${result.successful} successful cases.`,
        'success'
      );
    } catch (err) {
      addToast(err?.error?.message || 'Batch recovery failed', 'error');
    } finally {
      setActiveAction(null);
    }
  };

  const handleSimulateFailure = async () => {
    setActiveAction('failure');
    try {
      await api.simulateFailure();
      setFailureArmed(true);
      addToast('⚠️ Failure simulation ARMED. Next execution will escalate.', 'warning');
    } catch (err) {
      addToast(err?.error?.message || 'Failed to arm simulation', 'error');
    } finally {
      setActiveAction(null);
    }
  };

  const handleExecuteCase = async (caseId) => {
    try {
      const result = await api.executeCase(caseId);
      if (result.status === 'NEEDS_HUMAN_REVIEW' || result.status === 'ESCALATED') {
        addToast(`ESCALATED TO HUMAN — ${result.message}`, 'error');
      } else if (result.status === 'RECOVERED') {
        addToast(
          `✓ Recovered ₹${result.amount_recovered.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`,
          'success'
        );
      } else if (result.status === 'HALTED') {
        addToast('Case halted — invalid card detected.', 'warning');
      } else {
        addToast(`Execution result: ${result.status}`, 'info');
      }
      await refreshAll();
      await fetchFailureStatus();
      // Refresh selected case if open
      if (selectedCase && selectedCase.id === caseId) {
        const updated = await api.getCase(caseId);
        setSelectedCase(updated);
      }
    } catch (err) {
      addToast(err?.error?.message || 'Execution failed', 'error');
    }
  };

  if (loading) {
    return (
      <div className="layout" style={{ alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
        <div style={{ textAlign: 'center' }}>
          <div className="spinner" style={{ margin: '0 auto var(--space-4)' }} />
          <div style={{ color: 'var(--color-text-muted)', fontSize: '14px' }}>
            Connecting to RecoverAI backend…
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="layout">
      <SandboxBanner />
      <Navbar providers={providers} />

      <main className="main-content">
        {error && (
          <div className="error-banner">
            <AlertTriangle size={18} style={{ flexShrink: 0 }} />
            <div>
              <strong>Backend Connection Error</strong>
              <div style={{ marginTop: 4, opacity: 0.8 }}>{error}</div>
            </div>
          </div>
        )}

        {failureArmed && (
          <div className="failure-armed-banner">
            <AlertTriangle size={18} />
            ⚠ FAILURE SIMULATION ARMED — NEXT EXECUTION WILL ESCALATE
          </div>
        )}

        <MetricsGrid dashboard={dashboard} />

        <ActionCenter
          onSeed={handleSeed}
          onReset={handleReset}
          onBatch={handleBatch}
          onSimulateFailure={handleSimulateFailure}
          onViewAudit={() => setShowAudit(true)}
          onRefresh={refreshAll}
          activeAction={activeAction}
          failureArmed={failureArmed}
          hasCases={cases.length > 0}
        />

        <CasesTable
          cases={cases}
          onSelectCase={setSelectedCase}
          onExecute={handleExecuteCase}
        />
      </main>

      {selectedCase && (
        <CaseDetailDrawer
          caseId={selectedCase.id}
          onClose={() => setSelectedCase(null)}
          onExecute={handleExecuteCase}
        />
      )}

      {showAudit && (
        <AuditDrawer onClose={() => setShowAudit(false)} />
      )}

      {batchResult && (
        <BatchResultModal
          result={batchResult}
          onClose={() => setBatchResult(null)}
        />
      )}

      <Toast toasts={toasts} onRemove={removeToast} />
    </div>
  );
}

export default App;
