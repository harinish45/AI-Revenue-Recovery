import React from 'react';

export function NoticeList({ notices, dismissNotice }) {
  return notices.map(notice => (
    <div key={notice.id} className={`notice ${notice.type}`} role="status">
      <strong>{notice.type === 'error' ? 'Escalation' : notice.type === 'warning' ? 'Warning' : 'Success'}</strong>
      <span>{notice.text}</span>
      <button onClick={() => dismissNotice(notice.id)} aria-label="Dismiss notification">×</button>
    </div>
  ));
}
