(() => {
  'use strict';
  if (window.location.pathname !== '/') return;

  const key = 'domain-monitor-dashboard-position';
  const currentHref = () => window.location.pathname + window.location.search;
  if ('scrollRestoration' in history) history.scrollRestoration = 'manual';

  function savePosition(reason, domainId = '') {
    sessionStorage.setItem(key, JSON.stringify({
      href: currentHref(),
      y: window.scrollY,
      domainId: String(domainId || ''),
      reason,
      savedAt: Date.now()
    }));
  }

  function restorePosition() {
    const raw = sessionStorage.getItem(key);
    if (!raw) return;
    sessionStorage.removeItem(key);
    let saved;
    try { saved = JSON.parse(raw); } catch (_) { return; }
    if (!saved || saved.href !== currentHref()) return;
    if (!Number.isFinite(saved.y) || Date.now() - Number(saved.savedAt || 0) > 120000) return;

    requestAnimationFrame(() => requestAnimationFrame(() => {
      const maximum = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
      window.scrollTo({top: Math.min(Math.max(0, saved.y), maximum), left: 0, behavior: 'auto'});
    }));
  }

  document.addEventListener('submit', event => {
    const form = event.target.closest('form.domain-check-form');
    if (!form) return;
    const button = form.querySelector('button');
    if (button) { button.disabled = true; button.textContent = 'Check queued'; }
    savePosition('check-now', form.dataset.domainId || '');
  });

  const refresh = document.getElementById('dashboard-refresh');
  if (refresh) refresh.addEventListener('click', () => savePosition('refresh'));

  restorePosition();
})();
