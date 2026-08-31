import React from 'react';

export class ErrorBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed ? (
      <div className="error-state">
        <h2>RecoverAI needs a refresh</h2>
        <p>The interface hit an unexpected data-shape error. No money action was executed.</p>
        <button className="primary-btn" onClick={() => window.location.reload()}>Reload demo</button>
      </div>
    ) : this.props.children;
  }
}
