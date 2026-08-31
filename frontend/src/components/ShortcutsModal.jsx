import React from 'react';

export function ShortcutsModal({ shortcutsOpen, onClose }) {
  if (!shortcutsOpen) return null;
  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className="case-modal shortcuts-modal" onMouseDown={event => event.stopPropagation()} role="dialog" aria-label="Keyboard shortcuts">
        <div className="modal-header"><div><div className="eyebrow">Operator controls</div><h2>Keyboard shortcuts</h2></div><button className="close-btn" onClick={onClose} aria-label="Close">×</button></div>
        <div className="shortcut-list"><div><kbd>?</kbd><span>Open this help panel</span></div><div><kbd>Esc</kbd><span>Close any open panel</span></div><div><kbd>Ctrl / ⌘ K</kbd><span>Open the full agent cockpit</span></div></div>
        <p className="modal-footnote">Shortcuts never execute a money action. Recovery actions remain behind explicit buttons and backend policy gates.</p>
      </div>
    </div>
  );
}
