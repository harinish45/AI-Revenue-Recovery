import React from 'react';
import {
  IndianRupee, TrendingUp, AlertCircle, CheckCircle2,
  Clock, BarChart3, Activity, XCircle
} from 'lucide-react';

function formatINR(amount) {
  if (amount === null || amount === undefined) return '—';
  return amount.toLocaleString('en-IN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

function MetricCard({ label, value, prefix, suffix, variant, icon: Icon, sub }) {
  return (
    <div className={`metric-card metric-card--${variant || 'default'}`}>
      <div className="metric-label">
        {Icon && <Icon size={12} />}
        {label}
      </div>
      <div className={`metric-value ${prefix === '₹' ? 'metric-value--currency' : ''}`}>
        {prefix !== '₹' && prefix && <span style={{ fontSize: '18px', color: 'var(--color-text-secondary)' }}>{prefix}</span>}
        {value ?? '—'}
        {suffix && <span style={{ fontSize: '16px', color: 'var(--color-text-secondary)', marginLeft: '2px' }}>{suffix}</span>}
      </div>
      {sub && <div className="metric-sub">{sub}</div>}
      {Icon && (
        <div className="metric-icon">
          <Icon size={64} />
        </div>
      )}
    </div>
  );
}

export default function MetricsGrid({ dashboard }) {
  const d = dashboard || {};

  const atRisk = d.total_at_risk != null ? `₹${formatINR(d.total_at_risk)}` : '—';
  const recovered = d.total_recovered != null ? `₹${formatINR(d.total_recovered)}` : '—';

  return (
    <div className="metrics-grid">
      <MetricCard
        label="Total Payments"
        value={d.total_payments ?? '—'}
        variant="default"
        icon={BarChart3}
        sub="In database"
      />
      <MetricCard
        label="Revenue at Risk"
        value={d.total_at_risk != null ? formatINR(d.total_at_risk) : '—'}
        prefix="₹"
        variant="warning"
        icon={AlertCircle}
        sub="Failed + abandoned payments"
      />
      <MetricCard
        label="Total Recovered"
        value={d.total_recovered != null ? formatINR(d.total_recovered) : '—'}
        prefix="₹"
        variant="success"
        icon={TrendingUp}
        sub="Via recovery actions"
      />
      <MetricCard
        label="Recovery Rate"
        value={d.recovery_rate_percent != null ? d.recovery_rate_percent.toFixed(1) : '—'}
        suffix="%"
        variant="info"
        icon={Activity}
        sub="Recovered / at-risk"
      />
      <MetricCard
        label="Open Cases"
        value={d.open_cases ?? '—'}
        variant="warning"
        icon={Clock}
        sub="Awaiting recovery"
      />
      <MetricCard
        label="Escalated"
        value={d.escalated_cases ?? '—'}
        variant="danger"
        icon={AlertCircle}
        sub="Needs human review"
      />
      <MetricCard
        label="Successful"
        value={d.successful_recoveries ?? '—'}
        variant="success"
        icon={CheckCircle2}
        sub="Recovery attempts"
      />
      <MetricCard
        label="Failed"
        value={d.failed_recoveries ?? '—'}
        variant="danger"
        icon={XCircle}
        sub="Recovery attempts"
      />
    </div>
  );
}
