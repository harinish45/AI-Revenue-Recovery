import React from 'react';

export function TopBar({ live, loading, refresh, seed, reset, openShortcuts }) {
  return (
    <>
      <div className="test-banner">
        <span className="warning-dot">●</span>
        <strong>Razorpay Hackathon Sandbox</strong>
        <span>|</span>
        <strong>Test Mode Active</strong>
        <span>|</span>
        <span>Simulated Gateway</span>
      </div>

      <header className="topbar">
        <div>
          <div className="eyebrow">Razorpay Hackathon · Track 03</div>
          <h1>RecoverAI <span>— Autonomous Revenue Recovery</span></h1>
          <p className="subtitle">Detect → Diagnose → Decide → Recover → Audit</p>
        </div>
        <div className="top-actions">
          <span className={`connection-state ${live ? 'online' : 'demo'}`}><span />{live ? 'Backend connected' : 'Demo fallback'}</span>
          {!live && <button className="ghost-btn" disabled={loading} onClick={refresh} title="Retry API connection">Retry Connection</button>}
          <button className="ghost-btn shortcut-btn" onClick={openShortcuts} title="Keyboard shortcuts">? Shortcuts</button>
          <button className="ghost-btn" disabled={loading} onClick={seed}>Seed Data</button>
          <button className="ghost-btn" disabled={loading} onClick={reset}>Reset</button>
        </div>
      </header>
    </>
  );
}
