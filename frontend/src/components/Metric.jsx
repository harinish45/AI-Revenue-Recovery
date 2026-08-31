import React from 'react';
import { money } from '../utils/format';

export function Metric({ label, value }) {
  const [shown, setShown] = React.useState(0);
  React.useEffect(() => {
    const target = Number(value) || 0; const started = performance.now(); let frame;
    const tick = now => { const progress = Math.min(1, (now - started) / 800); setShown(target * (1 - Math.pow(1 - progress, 3))); if (progress < 1) frame = requestAnimationFrame(tick); };
    frame = requestAnimationFrame(tick); return () => cancelAnimationFrame(frame);
  }, [value]);
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{label === 'Recovery rate' ? `${shown.toFixed(1)}%` : label.includes('cases') ? Math.round(shown) : money(shown)}</div>
    </div>
  );
}
