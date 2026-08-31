import React from 'react';
import { api } from '../api';
import { TERMINAL_STATES } from '../constants';
import { money, pretty } from '../utils/format';

export function useCaseExecution({ refresh, pushNotice, runAction, setSelected, setLoading }) {
  const [inFlight, setInFlight] = React.useState({});
  const [failureArmed, setFailureArmed] = React.useState(false);

  const execute = async item => {
    const statusStr = String(item.status || item.recovery_status || '').toLowerCase();
    if (TERMINAL_STATES.includes(statusStr)) {
      pushNotice({ type: 'warning', text: `Case #${item.id} is already ${pretty(statusStr)}.` });
      return;
    }
    if (inFlight[item.id]) return;
    setInFlight(previous => ({ ...previous, [item.id]: true }));
    setLoading(true);
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
      setInFlight(previous => ({ ...previous, [item.id]: false }));
      setLoading(false);
    }
  };

  const arm = async () => {
    const r = await runAction(api.simulateFailure, 'Gateway failure detected. Safely escalated to human review.', 'warning');
    if (r) setFailureArmed(true);
  };

  return { inFlight, failureArmed, setFailureArmed, execute, arm };
}
