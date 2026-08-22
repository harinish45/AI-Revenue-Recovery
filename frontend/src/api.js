const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload?.detail || payload?.error?.message || payload?.message || 'Request failed.';
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
  }
  return payload;
}

const normalizeQuery = (params) => String(params || '').replaceAll('page_size=', 'limit=');
const normalizeCase = (item) => ({
  ...item,
  customer: item.customer || { id: item.customer_id, name: item.customer_name || 'Unknown' },
  risk_level: String(item.risk_level || '').toUpperCase(),
  recommended_action: String(item.recommended_action || '').toUpperCase(),
  status: String(item.status || item.recovery_status || item.action_status || '').toUpperCase(),
  max_retries: item.max_retries ?? 2,
});
const normalizeCases = (payload) => {
  const items = Array.isArray(payload) ? payload : (payload?.items || []);
  return { ...(Array.isArray(payload) ? {} : payload), items: items.map(normalizeCase) };
};
const normalizeAudit = (payload) => {
  const items = Array.isArray(payload) ? payload : (payload?.items || []);
  return { ...(Array.isArray(payload) ? {} : payload), items: items.map((event) => ({ ...event, event_type: String(event.event_type || '').toUpperCase(), result: String(event.result || '').toUpperCase() })) };
};

export const api = {
  getDashboard: () => request('/dashboard/summary'),
  getCases: (params = '') => request(`/cases/${normalizeQuery(params)}`).then(normalizeCases),
  getCase: (id) => request(`/cases/${id}`).then(normalizeCase),
  executeRecovery: (id) => request('/execution/execute', { method: 'POST', body: JSON.stringify({ case_id: Number(id) }) }),
  getAudit: (params = '') => request(`/audit/${normalizeQuery(params)}`).then(normalizeAudit),
  seedDemo: () => request('/demo/seed', { method: 'POST' }),
  resetDemo: () => request('/demo/reset', { method: 'POST' }),
  runRecoveryBatch: () => request('/batch/process', { method: 'POST', body: JSON.stringify({}) }),
};
