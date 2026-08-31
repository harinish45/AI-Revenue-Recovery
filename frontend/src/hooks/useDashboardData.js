import React from 'react';
import { api } from '../api';
import { DEFAULT_SUMMARY } from '../constants';

// Map backend dashboard fields onto the names this UI renders.
const mapSummary = s => ({
  ...s,
  total_at_risk: s.total_at_risk ?? s.revenue_at_risk ?? 0,
  total_recovered: s.total_recovered ?? s.recovered_amount ?? 0,
  recovery_rate_percent: s.recovery_rate_percent ?? s.recovery_rate ?? 0,
  open_cases: s.open_cases ?? 0,
  escalated_cases: s.escalated_cases ?? 0,
});

// Owns the dashboard summary/cases/audit reads plus the mutations (seed,
// reset, and the generic `runAction` wrapper) that other hooks compose with.
export function useDashboardData(pushNotice) {
  const [summary, setSummary] = React.useState(DEFAULT_SUMMARY);
  const [cases, setCases] = React.useState([]);
  const [audit, setAudit] = React.useState([]);
  const [loading, setLoading] = React.useState(false);
  const [booting, setBooting] = React.useState(true);
  const [live, setLive] = React.useState(false);
  const [lastUpdated, setLastUpdated] = React.useState(null);

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
    } finally {
      setBooting(false);
    }
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  // Generic action wrapper: loading state + success/error toast + refresh.
  const runAction = async (fn, text, type = 'success') => {
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

  const seed = () => runAction(api.seedDemo, '100 synthetic payments seeded successfully.');

  // onOtherStateReset lets the composing component clear state this hook
  // doesn't own (e.g. failureArmed, batchResult) as part of one reset.
  const reset = async onOtherStateReset => {
    setLoading(true);
    try {
      await api.resetDemo();
      onOtherStateReset?.();
      setCases([]);
      setAudit([]);
      setSummary(DEFAULT_SUMMARY);
      pushNotice({ type: 'success', text: 'Database reset. Re-seeding demo data...' });
      await api.seedDemo();
      await refresh();
    } catch (e) {
      pushNotice({ type: 'error', text: e.message });
    } finally {
      setLoading(false);
    }
  };

  return {
    summary, cases, audit, setAudit,
    loading, setLoading, booting, live, lastUpdated,
    refresh, runAction, seed, reset,
  };
}
