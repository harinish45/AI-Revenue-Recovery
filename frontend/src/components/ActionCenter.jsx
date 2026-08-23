import React from 'react';
import {
  Database, Trash2, Zap, AlertTriangle, FileText,
  RefreshCw, Loader
} from 'lucide-react';

function Btn({ onClick, disabled, loading, variant, icon: Icon, children }) {
  return (
    <button
      id={`action-btn-${children?.toString().toLowerCase().replace(/\s+/g, '-')}`}
      className={`btn btn--${variant} ${loading ? 'btn--loading' : ''}`}
      onClick={onClick}
      disabled={disabled || loading}
    >
      {loading
        ? <Loader size={14} className="btn-spinner" />
        : Icon && <Icon size={14} />
      }
      {children}
    </button>
  );
}

export default function ActionCenter({
  onSeed, onReset, onBatch, onSimulateFailure, onViewAudit, onRefresh,
  activeAction, failureArmed, hasCases,
}) {
  return (
    <div className="action-center">
      <span className="action-center-label">Actions</span>

      <Btn
        onClick={onSeed}
        loading={activeAction === 'seed'}
        variant="primary"
        icon={Database}
        id="btn-seed"
      >
        Seed Demo Data
      </Btn>

      <Btn
        onClick={onReset}
        loading={activeAction === 'reset'}
        variant="ghost"
        icon={Trash2}
      >
        Reset Demo
      </Btn>

      <Btn
        onClick={onBatch}
        loading={activeAction === 'batch'}
        disabled={!hasCases}
        variant="success"
        icon={Zap}
      >
        Run Batch Recovery
      </Btn>

      <Btn
        onClick={onSimulateFailure}
        loading={activeAction === 'failure'}
        disabled={failureArmed}
        variant={failureArmed ? 'danger' : 'warning'}
        icon={AlertTriangle}
      >
        {failureArmed ? '⚠ FAILURE SIMULATION ARMED' : 'Arm Failure Simulation'}
      </Btn>

      <Btn
        onClick={onViewAudit}
        variant="ghost"
        icon={FileText}
      >
        View Compliance Audit
      </Btn>

      <Btn
        onClick={onRefresh}
        variant="ghost"
        icon={RefreshCw}
      >
        Refresh
      </Btn>
    </div>
  );
}
