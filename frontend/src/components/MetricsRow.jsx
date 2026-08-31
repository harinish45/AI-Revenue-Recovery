import React from 'react';
import { Metric } from './Metric';

export function MetricsRow({ summary, booting, healthScore }) {
  return (
    <>
      {booting && <div className="loading-skeleton" aria-label="Loading dashboard"><i /><i /><i /><i /><i /></div>}
      <section className={`metrics-grid ${booting ? 'is-loading' : ''}`} aria-label="Dashboard metrics">
        <Metric label="Total at risk" value={summary.total_at_risk} />
        <Metric label="Total recovered" value={summary.total_recovered} />
        <Metric label="Recovery rate" value={summary.recovery_rate_percent ?? 0} />
        <Metric label="Open cases" value={summary.open_cases ?? 0} />
        <Metric label="Escalated cases" value={summary.escalated_cases ?? 0} />
        <div className={`health-score-card ${healthScore >= 75 ? 'healthy' : healthScore >= 50 ? 'watch' : 'critical'}`}>
          <div className="metric-label">Recovery Health Score</div>
          <div className="health-score-value">{healthScore}<small>/100</small></div>
          <div className="health-score-bar"><span style={{ width: `${healthScore}%` }} /></div>
          <span>{healthScore >= 75 ? 'Healthy operating signal' : healthScore >= 50 ? 'Watch intervention quality' : 'Needs operator attention'}</span>
        </div>
      </section>
    </>
  );
}
