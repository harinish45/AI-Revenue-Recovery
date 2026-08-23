/**
 * api.js — RecoverAI API client
 *
 * All API calls go through this module.
 * Error responses are normalized to { error: { code, message } }
 * so the UI always receives a consistent shape.
 */

const BASE_URL = import.meta.env.VITE_API_BASE || '';

async function request(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== undefined) {
    opts.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, opts);
  } catch (networkErr) {
    throw {
      error: {
        code: 'NETWORK_ERROR',
        message: `Cannot reach RecoverAI backend. Is it running? (${networkErr.message})`,
      },
    };
  }

  if (!response.ok) {
    let errBody;
    try {
      errBody = await response.json();
    } catch {
      errBody = { detail: response.statusText };
    }
    throw {
      error: {
        code: `HTTP_${response.status}`,
        message:
          errBody?.error?.message ||
          errBody?.detail ||
          `Request failed with HTTP ${response.status}`,
      },
    };
  }

  return response.json();
}

// ---------------------------------------------------------------------------
// Demo
// ---------------------------------------------------------------------------
export const api = {
  seedDemo: () => request('POST', '/api/demo/seed'),
  resetDemo: () => request('POST', '/api/demo/reset'),
  runBatch: () => request('POST', '/api/demo/recovery-batch'),
  simulateFailure: () => request('POST', '/api/demo/simulate-failure'),
  getFailureStatus: () => request('GET', '/api/demo/failure-status'),

  // Dashboard
  getDashboard: () => request('GET', '/api/dashboard/summary'),

  // Cases
  getCases: (status) => {
    const qs = status ? `?status=${status}` : '';
    return request('GET', `/api/cases/${qs}`);
  },
  getCase: (caseId) => request('GET', `/api/cases/${caseId}`),

  // Execution
  executeCase: (caseId) =>
    request('POST', '/api/execution/execute', { case_id: caseId }),

  // Audit
  getAudit: (limit = 200) => request('GET', `/api/audit/?limit=${limit}`),

  // Health
  getHealth: () => request('GET', '/health'),

  // Providers
  getProviders: () => request('GET', '/api/providers'),
};
