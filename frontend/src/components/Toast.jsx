import React from 'react';
import { CheckCircle2, XCircle, AlertTriangle, Info } from 'lucide-react';

const ICONS = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

const COLORS = {
  success: 'var(--color-success)',
  error: 'var(--color-danger)',
  warning: 'var(--color-warning)',
  info: 'var(--color-info)',
};

function ToastItem({ toast, onRemove }) {
  const Icon = ICONS[toast.type] || Info;
  const color = COLORS[toast.type] || 'var(--color-info)';

  return (
    <div className={`toast toast--${toast.type}`} role="alert">
      <Icon size={16} style={{ color, flexShrink: 0 }} />
      <span className="toast-message">{toast.message}</span>
      <button
        style={{ all: 'unset', cursor: 'pointer', color: 'var(--color-text-muted)', flexShrink: 0 }}
        onClick={() => onRemove(toast.id)}
        aria-label="Dismiss"
      >
        ✕
      </button>
    </div>
  );
}

export default function Toast({ toasts, onRemove }) {
  if (!toasts || toasts.length === 0) return null;
  return (
    <div className="toast-container" aria-live="polite">
      {toasts.map(t => (
        <ToastItem key={t.id} toast={t} onRemove={onRemove} />
      ))}
    </div>
  );
}
