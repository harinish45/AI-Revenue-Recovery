export const RISKS = ['all', 'LOW', 'MEDIUM', 'HIGH'];

// Mirrors backend/app/services/policy_engine.py's TERMINAL_STATES exactly --
// missing 'awaiting_payment' or 'closed' here used to mean the Execute
// button stayed visible on those cases, and useCaseExecution's pre-check
// wouldn't catch a click before hitting the API. The backend correctly
// blocks it either way (policy_check_failed), but for awaiting_payment
// specifically the blocked response's status is still "awaiting_payment",
// which the UI misread as "intervention just sent" -- a false success
// message for a click that actually did nothing.
export const TERMINAL_STATES = ['recovered', 'blocked', 'needs_human_review', 'skipped', 'awaiting_payment', 'closed'];

// Shared shape for the dashboard summary metrics, used both as initial React
// state and as the reset target after Api.resetDemo() clears the backend.
export const DEFAULT_SUMMARY = {
  total_at_risk: 0,
  total_recovered: 0,
  recovery_rate_percent: 0,
  open_cases: 0,
  escalated_cases: 0,
};
