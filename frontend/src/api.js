const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

async function request(path, options = {}) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const message = payload?.detail || payload?.error?.message || payload?.message || 'Request failed.';
      throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
    }
    return payload;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('RecoverAI backend timed out. Showing safe demo data.');
    if (error instanceof TypeError) throw new Error('Unable to reach RecoverAI backend. Showing safe demo data.');
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
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

const FINAL_EXECUTION_STATES = ['recovered', 'failed', 'needs_human_review', 'blocked', 'skipped', 'awaiting_payment'];

export const api = {
  getDashboard: () => request('/api/dashboard/summary'),
  getCases: () => request('/api/cases?limit=100').then(normalizeCases),
  getCase: (id) => request(`/api/cases/${id}`).then(normalizeCase),
  // Backend contract explicitly accepts JSON: { "case_id": "<OPEN_CASE_ID>" }.
  //
  // Idempotency contract: ONE key is generated per user action and reused for
  // every retry of that action until a FINAL response arrives. A timeout after
  // the backend completed therefore can never trigger a second recovery.
  executeRecovery: (id) => {
    if (!executeRecovery.keys) executeRecovery.keys = {};
    if (!executeRecovery.keys[id]) {
      executeRecovery.keys[id] = `recoverai-react-${id}-${crypto.randomUUID()}`;
    }
    return request('/api/execution/execute', {
      method: 'POST',
      body: JSON.stringify({ case_id: String(id) }),
      headers: { 'Idempotency-Key': executeRecovery.keys[id] },
    }).then(
      (payload) => {
        const status = String(payload?.status || '').toLowerCase();
        if (FINAL_EXECUTION_STATES.includes(status)) delete executeRecovery.keys[id];
        return payload;
      },
      (error) => error
    ).then((result) => {
      if (result instanceof Error) throw result;
      return result;
    });
  },
  confirmProviderPayment: (id) => request(`/api/execution/cases/${encodeURIComponent(id)}/confirm-payment`, { method: 'POST' }),
  getAudit: () => request('/api/audit?limit=200').then(normalizeAudit),
  verifyAudit: id => request(`/api/audit/${encodeURIComponent(id)}/verify`),
  seedDemo: () => request('/api/demo/seed', { method: 'POST' }),
  resetDemo: () => request('/api/demo/reset', { method: 'POST' }),
  runRecoveryBatch: () => request('/api/demo/recovery-batch', { method: 'POST' }),
  simulateFailure: () => request('/api/demo/simulate-failure', { method: 'POST' }),
};
