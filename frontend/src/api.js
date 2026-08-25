const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

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

const toOpen = (s) => (String(s || '').toUpperCase() === 'PENDING' ? 'OPEN' : String(s || '').toUpperCase());
const normalizeCase = (item) => ({
  ...item,
  customer: item.customer || { id: item.customer_id, name: item.customer_name || item.payment?.customer_name || 'Unknown' },
  amount: item.amount ?? item.payment?.amount ?? item.amount_at_risk ?? 0,
  risk_level: String(item.risk_level || '').toUpperCase(),
  recommended_action: String(item.recommended_action || '').toUpperCase(),
  status: toOpen(item.status || item.recovery_status || item.action_status || ''),
  max_retries: item.max_retries ?? 2,
});
const normalizeCases = (payload) => {
  const items = Array.isArray(payload) ? payload : (payload?.items || []);
  return { ...(Array.isArray(payload) ? {} : payload), items: items.map(normalizeCase) };
};
const normalizeAudit = (payload) => {
  const items = Array.isArray(payload) ? payload : (payload?.items || []);
  return { ...(Array.isArray(payload) ? {} : payload), items: items.map((event) => ({
    ...event,
    event_type: String(event.event_type || '').toUpperCase(),
    result: String(event.result || '').toUpperCase(),
  })) };
};

export const api = {
  getDashboard: () => request('/api/dashboard/summary'),
  getCases: () => request('/api/cases?limit=100').then(normalizeCases),
  getCase: (id) => request(`/api/cases/${id}`).then(normalizeCase),
  // Backend contract explicitly accepts JSON: { "case_id": "<OPEN_CASE_ID>" }.
  executeRecovery: (id) => request('/api/execution/execute', {
    method: 'POST',
    body: JSON.stringify({ case_id: String(id) }),
    headers: { 'Idempotency-Key': `recoverai-react-${id}-${Date.now()}` },
  }),
  getAudit: () => request('/api/audit?limit=200').then(normalizeAudit),
  verifyAudit: id => request(`/api/audit/${encodeURIComponent(id)}/verify`),
  seedDemo: () => request('/api/demo/seed', { method: 'POST' }),
  resetDemo: () => request('/api/demo/reset', { method: 'POST' }),
  runRecoveryBatch: () => request('/api/demo/recovery-batch', { method: 'POST' }),
  simulateFailure: () => request('/api/demo/simulate-failure', { method: 'POST' }),
};
