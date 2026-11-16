(() => {
  'use strict';
  if (window.location.pathname !== '/') return;
  const forms = [...document.querySelectorAll('form.domain-check-form[data-pending="1"]')];
  if (!forms.length) return;
  const ids = forms.map(f => f.dataset.domainId).filter(x => /^\d+$/.test(x)).slice(0, 200);
  if (!ids.length) return;
  const key = 'domain-monitor-dashboard-position';
  let busy = false, stopped = false;
  function batchActive() {
    const panel = document.getElementById('check-progress');
    return panel && !panel.hidden;
  }
  async function poll() {
    if (busy || stopped) return;
    busy = true;
    try {
      const r = await fetch('/domains/status?ids=' + encodeURIComponent(ids.join(',')),
        {credentials: 'same-origin', cache: 'no-store'});
      if (!r.ok) return;
      const data = (await r.json()).domains || {};
      let finished = false;
      for (const form of forms) {
        const item = data[form.dataset.domainId];
        const button = form.querySelector('button');
        if (!item || !button) continue;
        if (item.pending) {
          button.textContent = item.checking ? 'Checking\u2026' : 'Check queued';
        } else if (form.dataset.pending === '1') {
          form.dataset.pending = '0';
          finished = true;
          if (batchActive()) button.textContent = 'Updated - refresh to view';
        }
      }
      // During Check all, avoid reloading after every domain.
      if (finished && !batchActive()) {
        stopped = true;
        sessionStorage.setItem(key, JSON.stringify({
          href: window.location.pathname + window.location.search,
          y: window.scrollY, domainId: '', reason: 'auto-update', savedAt: Date.now()
        }));
        window.location.reload();
      }
    } catch (e) {
    } finally {
      busy = false;
    }
  }
  poll();
  setInterval(poll, 3000);
})();
