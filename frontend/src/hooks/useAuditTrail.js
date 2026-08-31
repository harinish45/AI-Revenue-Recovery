import React from 'react';
import { api } from '../api';

export function useAuditTrail({ audit, setAudit, pushNotice }) {
  const [auditOpen, setAuditOpen] = React.useState(false);
  const [sealStatus, setSealStatus] = React.useState({});

  const openAuditDrawer = async () => {
    setAuditOpen(true);
    try {
      const a = await api.getAudit();
      setAudit(a.items || []);
    } catch {
      /* retain state on failure */
    }
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
    audit.forEach(event =>
      rows.push([event.id, event.case_id || '', event.event_type, event.actor || '', event.result || '', event.timestamp || ''])
    );
    const csv = rows.map(row => row.map(value => `"${String(value ?? '').replaceAll('"', '""')}"`).join(',')).join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'recoverai-audit.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  return { auditOpen, setAuditOpen, openAuditDrawer, sealStatus, verifySeal, exportAudit };
}
