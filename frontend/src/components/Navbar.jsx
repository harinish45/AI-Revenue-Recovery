import React from 'react';
import { Brain, Cpu } from 'lucide-react';

export default function Navbar({ providers }) {
  const activeProviders = providers?.active || [];
  const primaryProvider = activeProviders[0] || 'deterministic';

  const providerLabel = {
    groq: 'AI: Groq',
    openrouter: 'AI: OpenRouter',
    nvidia_nim: 'AI: Nvidia NIM',
    openai: 'AI: OpenAI',
    deterministic_fallback: 'AI: Rules Engine',
  }[primaryProvider] || `AI: ${primaryProvider}`;

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <div className="navbar-logo">R</div>
        <div>
          <div className="navbar-title">RecoverAI</div>
          <div className="navbar-subtitle">Revenue Recovery Control Center</div>
        </div>
      </div>
      <div className="navbar-right">
        <div className="provider-badge">
          <Brain size={11} />
          {providerLabel}
        </div>
      </div>
    </nav>
  );
}
