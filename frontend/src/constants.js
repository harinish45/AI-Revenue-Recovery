export const RISKS = ['all', 'LOW', 'MEDIUM', 'HIGH'];

export const TERMINAL_STATES = ['recovered', 'blocked', 'needs_human_review', 'skipped'];

// Shared shape for the dashboard summary metrics, used both as initial React
// state and as the reset target after Api.resetDemo() clears the backend.
export const DEFAULT_SUMMARY = {
  total_at_risk: 0,
  total_recovered: 0,
  recovery_rate_percent: 0,
  open_cases: 0,
  escalated_cases: 0,
};
