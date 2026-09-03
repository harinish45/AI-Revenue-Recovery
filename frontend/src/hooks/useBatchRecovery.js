import React from 'react';
import { api } from '../api';
import { money } from '../utils/format';

export function useBatchRecovery({ cases, refresh, pushNotice, setLoading }) {
  const [batchResult, setBatchResult] = React.useState(null);
  const [progress, setProgress] = React.useState(0);

  const batch = async () => {
    const pendingCases = cases.filter(c => {
      const s = String(c.status || c.recovery_status || '').toLowerCase();
      return s === 'open' || s === 'pending';
    });
    if (pendingCases.length === 0) {
      pushNotice({ type: 'warning', text: 'No pending cases to recover.' });
      return;
    }
    setLoading(true);
    setProgress(8);
    const progressTimer = setInterval(() => setProgress(previous => Math.min(92, previous + 9)), 260);
    try {
      const r = await api.runRecoveryBatch();
      setBatchResult(r);
      clearInterval(progressTimer);
      setProgress(100);
      pushNotice({ type: 'success', text: 'Recovered ' + money(r.amount_recovered) + ' across ' + r.successful + ' successful cases.' });
      await refresh();
      return r;
    } catch (e) {
      clearInterval(progressTimer);
      setProgress(0);
      pushNotice({ type: 'error', text: e.message });
    } finally {
      setLoading(false);
      setTimeout(() => setProgress(0), 500);
    }
  };

  return { batchResult, setBatchResult, progress, batch };
}
