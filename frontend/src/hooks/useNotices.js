import React from 'react';

export function useNotices() {
  const [notices, setNotices] = React.useState([]);

  const pushNotice = notice =>
    setNotices(previous => [...previous, { ...notice, id: `${Date.now()}-${Math.random()}` }].slice(-4));

  const dismissNotice = id => setNotices(previous => previous.filter(item => item.id !== id));

  return { notices, pushNotice, dismissNotice };
}
