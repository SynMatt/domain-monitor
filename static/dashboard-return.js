(() => {
  'use strict';
  const viewKey = 'domain-monitor-dashboard-view';
  const pendingKey = 'domain-monitor-dashboard-return';
  const positionKey = 'domain-monitor-dashboard-position';
  const read = key => { try { return JSON.parse(sessionStorage.getItem(key)); } catch (_) { return null; } };
  const write = (key, value) => { try { sessionStorage.setItem(key, JSON.stringify(value)); } catch (_) {} };
  const remove = key => { try { sessionStorage.removeItem(key); } catch (_) {} };
  function validView(value) {
    if (!value || typeof value.href !== 'string' || !Number.isFinite(value.y) || value.y < 0) return null;
    try {
      const url = new URL(value.href, window.location.origin);
      if (url.origin !== window.location.origin || url.pathname !== '/' || url.hash) return null;
      return {href: url.pathname + url.search, y: value.y};
    } catch (_) { return null; }
  }
  const onDashboard = window.location.pathname === '/';
  const href = window.location.pathname + window.location.search;
  const saved = validView(read(viewKey));
  // This deferred asset loads before dashboard-position.js. Reuse its exact-scroll restoration.
  if (onDashboard) {
    const pending = validView(read(pendingKey));
    remove(pendingKey);
    if (pending && pending.href === href) {
      write(positionKey, {href, y: pending.y, domainId: '', reason: 'dashboard-return', savedAt: Date.now()});
    }
    const save = () => write(viewKey, {href, y: Math.max(0, window.scrollY)});
    window.addEventListener('pagehide', save);
    document.addEventListener('click', event => {
      if (event.target.closest('a[href]')) save();
    });
    document.addEventListener('submit', save);
    // Do not overwrite a saved return position before the existing script restores it.
    requestAnimationFrame(() => requestAnimationFrame(() => requestAnimationFrame(save)));
  }
  document.querySelectorAll('[data-dashboard-return]').forEach(link => {
    if (saved) link.setAttribute('href', saved.href);
    link.addEventListener('click', event => {
      if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      const view = onDashboard ? {href, y: Math.max(0, window.scrollY)} : validView(read(viewKey));
      if (view) {
        link.setAttribute('href', view.href);
        write(pendingKey, view);
      }
    });
  });
  document.addEventListener('submit', event => {
    const form = event.target.closest('form');
    if (form && new URL(form.action, window.location.origin).pathname === '/logout') {
      remove(viewKey); remove(pendingKey); remove(positionKey);
      // Prevent pagehide from repopulating the view after logout.
      window.addEventListener('pagehide', () => { remove(viewKey); remove(pendingKey); remove(positionKey); });
    }
  });
})();
