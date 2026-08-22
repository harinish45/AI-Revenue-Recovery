const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload?.error?.message || 'Request failed.';
    throw new Error(message);
  }
  return payload;
}

export const api = {
  getDashboard: () => request('/dashboard/summary'),
  getCases: (params = '') => request(`/recovery/cases${params}`),
  getCase: (id) => request(`/recovery/cases/${id}`),
  executeRecovery: (id) => request(`/recovery/cases/${id}/execute`, { method: 'POST' }),
  getAudit: (params = '') => request(`/recovery/audit${params}`),
  seedDemo: () => request('/demo/seed', { method: 'POST' }),
  resetDemo: () => request('/demo/reset', { method: 'POST' }),
  runRecoveryBatch: () => request('/demo/recovery-batch', { method: 'POST' }),
  simulateFailure: () => request('/demo/simulate-failure', { method: 'POST' }),
};
