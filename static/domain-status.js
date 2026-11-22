(() => {
  'use strict';
  const root = document.getElementById('domain-live-status');
  if (!root || !/^\d+$/.test(root.dataset.domainId)) return;
  const id = root.dataset.domainId;
  const key = 'domain-monitor-detail-position-' + id;
  const initial = root.dataset.checked === '' ? null : Number(root.dataset.checked);
  let sawPending = root.dataset.pending === '1';
  let dirty = false, busy = false, stopped = false, timer;
  const checkForm = document.querySelector('form[action="/domain/' + id + '/check"]');
  const button = checkForm && checkForm.querySelector('button');
  const rotation = document.querySelector('form.dm-rotation-mini');
  const date = rotation && rotation.querySelector('input[type="date"]');
  const originalDate = date ? date.value : '';
  const details = () => [...document.querySelectorAll('details')];
  // Restore only state explicitly saved immediately before our own reload.
  try {
    const saved = JSON.parse(sessionStorage.getItem(key));
    sessionStorage.removeItem(key);
    if (saved && saved.href === location.pathname + location.search && Date.now() - saved.at < 120000) {
      const nodes = details();
      if (Array.isArray(saved.open)) saved.open.forEach(i => {
        if (Number.isInteger(i) && nodes[i]) nodes[i].open = true;
      });
      if (Number.isFinite(saved.y)) requestAnimationFrame(() => requestAnimationFrame(() => {
        const max = Math.max(0, document.documentElement.scrollHeight - innerHeight);
        window.scrollTo({top: Math.min(Math.max(0, saved.y), max), behavior: 'auto'});
      }));
    }
  } catch (_) {}
  function feedback(pending, checking) {
    root.textContent = pending || checking ? (checking ? 'Checking domain...' : 'Domain check queued...') : '';
    if (button) {
      button.disabled = pending || checking;
      button.textContent = checking ? 'Checking...' : pending ? 'Check queued' : 'Check now';
    }
  }
  function reload() {
    if (dirty || (rotation && rotation.contains(document.activeElement))) {
      root.textContent = 'New results available. Finish editing the rotation date, then use Refresh to view them.';
      return;
    }
    try {
      sessionStorage.setItem(key, JSON.stringify({href: location.pathname + location.search,
        y: window.scrollY, open: details().flatMap((d, i) => d.open ? [i] : []), at: Date.now()}));
    } catch (_) {}
    stopped = true;
    window.location.reload();
  }
  if (date) date.addEventListener('input', () => { dirty = date.value !== originalDate; });
  if (checkForm) checkForm.addEventListener('submit', () => { sawPending = true; feedback(true, false); });
  feedback(sawPending, false);
  async function poll() {
    if (busy || stopped || document.hidden) return;
    busy = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch('/domains/status?ids=' + encodeURIComponent(id),
        {credentials: 'same-origin', cache: 'no-store', signal: controller.signal});
      if (response.status === 401 || response.status === 403 || response.redirected) { stopped = true; return; }
      if (!response.ok) return;
      const payload = await response.json();
      const item = payload.domains && payload.domains[id];
      if (!item) { stopped = true; root.textContent = 'Domain is no longer available. Return to Dashboard.'; return; }
      const pending = Boolean(item.pending || item.checking);
      if (pending) sawPending = true;
      feedback(Boolean(item.pending), Boolean(item.checking));
      const checked = item.checked == null ? null : Number(item.checked);
      if (!pending && ((Number.isFinite(checked) && checked !== initial) || sawPending)) reload();
    } catch (_) {
      // Temporary network errors must not trigger reloads or discard edits.
    } finally {
      clearTimeout(timeout);
      busy = false;
      if (!stopped) timer = setTimeout(poll, 3000);
    }
  }
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && !busy && !stopped) { clearTimeout(timer); poll(); }
  });
  window.addEventListener('pagehide', () => { stopped = true; clearTimeout(timer); });
  window.addEventListener('pageshow', event => {
    if (event.persisted) { stopped = false; clearTimeout(timer); poll(); }
  });
  poll();
})();
