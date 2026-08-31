import React from 'react';

export function useShortcuts() {
  const [shortcutsOpen, setShortcutsOpen] = React.useState(false);

  React.useEffect(() => {
    const onKeyDown = event => {
      const tag = event.target?.tagName;
      if (event.key === '?' && tag !== 'INPUT' && tag !== 'TEXTAREA') setShortcutsOpen(true);
      if (event.key === 'Escape') setShortcutsOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  return { shortcutsOpen, setShortcutsOpen };
}
