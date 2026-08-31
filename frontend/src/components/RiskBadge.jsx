import React from 'react';

export function RiskBadge({ risk }) {
  const r = String(risk || '').toUpperCase();
  const cls = r === 'HIGH' ? 'risk-high' : r === 'MEDIUM' ? 'risk-medium' : r === 'LOW' ? 'risk-low' : 'risk-unknown';
  return <span className={`risk-badge ${cls}`}>{r || 'UNKNOWN'}</span>;
}
