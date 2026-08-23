import React from 'react';
import { Zap, Shield, TestTube2 } from 'lucide-react';

export default function SandboxBanner() {
  return (
    <div className="sandbox-banner">
      <div className="sandbox-banner-left">
        <span className="sandbox-badge sandbox-badge--hackathon">
          <Zap size={10} />
          Razorpay Hackathon · Track 03
        </span>
        <span className="sandbox-badge sandbox-badge--testmode">
          <span className="pulse-dot" />
          Test Mode Active
        </span>
        <span className="sandbox-badge sandbox-badge--simulated">
          <TestTube2 size={10} />
          Simulated Gateway
        </span>
      </div>
      <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Shield size={11} />
        No real money is moved · All transactions are in Razorpay Test Mode
      </div>
    </div>
  );
}
