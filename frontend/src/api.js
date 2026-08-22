const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload?.error?.message || 'Request failed.');
  return payload;
}

const normalizeCase = (item) => ({
  ...item,
  customer: item.customer || { id: item.customer_id, name: item.customer_name || 'Unknown' },
  risk_level: String(item.risk_level || '').toUpperCase(),
  recommended_action: String(item.recommended_action || '').toUpperCase(),
  status: String(item.status || item.recovery_status || item.action_status || '').toUpperCase(),
  max_retries: item.max_retries ?? 2,
});

const normalizeCases = (payload) => ({ ...payload, items: (payload?.items || []).map(normalizeCase) });
const normalizeAudit = (payload) => ({ ...payload, items: (payload?.items || []).map((event) => ({ ...event, event_type: String(event.event_type || '').toUpperCase(), result: String(event.result || '').toUpperCase() })) });

export const api = {
  getDashboard: () => request('/dashboard/summary'),
  getCases: (params = '') => request(`/recovery/cases${params}`).then(normalizeCases),
  getCase: (id) => request(`/recovery/cases/${id}`).then(normalizeCase),
  executeRecovery: (id) => request(`/recovery/cases/${id}/execute`, { method: 'POST' }),
  getAudit: (params = '') => request(`/recovery/audit${params}`).then(normalizeAudit),
  seedDemo: () => request('/demo/seed', { method: 'POST' }),
  resetDemo: () => request('/demo/reset', { method: 'POST' }),
  runRecoveryBatch: () => request('/demo/recovery-batch', { method: 'POST' }),
  simulateFailure: () => request('/demo/simulate-failure', { method: 'POST' }),
};
