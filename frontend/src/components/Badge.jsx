import React from 'react';
import { pretty } from '../utils/format';

export function Badge({ status }) {
  const normalized = String(status || '').toLowerCase().replaceAll('_', ' ');
  const human = normalized === 'needs human review' || normalized === 'blocked';
  const awaiting = normalized === 'awaiting payment';
  return (
    <span className={`status-badge ${human ? 'needs-human-review' : String(status || '').toLowerCase()}`}>
      {human ? 'ESCALATED TO HUMAN' : awaiting ? 'AWAITING PAYMENT' : pretty(status)}
    </span>
  );
}
