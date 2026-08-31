import React from 'react';

export function useClipboard(pushNotice) {
  const [copied, setCopied] = React.useState(false);

  const copyToClipboard = async text => {
    try {
      if (navigator.clipboard && window.isSecureContext && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(String(text));
        setCopied(true);
        setTimeout(() => setCopied(false), 1800);
        return;
      }
      throw new Error('Clipboard API unavailable');
    } catch {
      // Fallback for non-secure contexts (HTTP)
      const ta = document.createElement('textarea');
      ta.value = String(text);
      ta.style.position = 'fixed';
      ta.style.top = '0';
      ta.style.left = '0';
      ta.style.opacity = '0';
      ta.setAttribute('readonly', '');
      document.body.appendChild(ta);
      ta.select();
      ta.setSelectionRange(0, 99999);
      try {
        const ok = document.execCommand('copy');
        if (ok) {
          setCopied(true);
          setTimeout(() => setCopied(false), 1800);
        } else {
          pushNotice({ type: 'warning', text: 'Copy failed.' });
        }
      } catch {
        pushNotice({ type: 'warning', text: 'Copy failed.' });
      }
      document.body.removeChild(ta);
    }
  };

  return { copied, copyToClipboard };
}
