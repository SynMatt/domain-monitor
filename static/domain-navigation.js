(() => {
  'use strict';
  const nav = document.getElementById('domain-sequence-nav');
  if (!nav || !/^\d+$/.test(nav.dataset.domainId)) return;
  const currentId = nav.dataset.domainId;
  const viewKey = 'domain-monitor-dashboard-view';
  let saved;
  try { saved = JSON.parse(sessionStorage.getItem(viewKey)); } catch (_) { return; }
  if (!saved || typeof saved.href !== 'string' || !Array.isArray(saved.ids)) return;
  let dashboardUrl;
  try { dashboardUrl = new URL(saved.href, window.location.origin); } catch (_) { return; }
  if (dashboardUrl.origin !== window.location.origin || dashboardUrl.pathname !== '/' || dashboardUrl.hash) return;
  const dedupe = values => [...new Set(values.filter(id => /^\d+$/.test(String(id))).slice(0, 1000).map(String))];
  const oldIds = dedupe(saved.ids);
  const oldIndex = oldIds.indexOf(currentId);
  if (oldIndex < 0) return;
  const previous = document.getElementById('previous-domain');
  const next = document.getElementById('next-domain');
  const position = document.getElementById('domain-sequence-position');
  function setLink(link, id) {
    if (id) {
      link.href = '/domain/' + encodeURIComponent(id);
      link.removeAttribute('aria-disabled');
      link.removeAttribute('tabindex');
    } else {
      link.href = '#';
      link.setAttribute('aria-disabled', 'true');
      link.setAttribute('tabindex', '-1');
    }
  }
  function render(ids) {
    const current = ids.indexOf(currentId);
    if (current >= 0) {
      setLink(previous, ids[current - 1]);
      setLink(next, ids[current + 1]);
      position.textContent = (current + 1) + ' of ' + ids.length + ' in current dashboard view';
    } else {
      // The current domain was resolved or otherwise stopped matching. Use its old
      // neighbours to find the closest remaining domains without skipping an item.
      const before = oldIds.slice(0, oldIndex).reverse().find(id => ids.includes(id));
      const after = oldIds.slice(oldIndex + 1).find(id => ids.includes(id));
      setLink(previous, before);
      setLink(next, after);
      position.textContent = ids.length ? 'No longer matches filter · ' + ids.length + ' remaining' : 'No domains match this filter';
    }
    nav.hidden = false;
  }
  // Render immediately from the saved sequence, then replace it with fresh server-rendered
  // dashboard results. This deliberately reuses the dashboard's exact filters and sort order.
  render(oldIds);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  fetch(dashboardUrl.pathname + dashboardUrl.search,
    {credentials: 'same-origin', cache: 'no-store', signal: controller.signal})
    .then(response => {
      if (!response.ok || response.redirected) throw new Error('Dashboard unavailable');
      return response.text();
    })
    .then(html => {
      const documentCopy = new DOMParser().parseFromString(html, 'text/html');
      const ids = dedupe([...documentCopy.querySelectorAll('.grid article.card h2 a[href^="/domain/"]')]
        .map(link => (link.getAttribute('href') || '').match(/^\/domain\/(\d+)$/))
        .filter(Boolean).map(match => match[1]));
      saved.ids = ids;
      try { sessionStorage.setItem(viewKey, JSON.stringify(saved)); } catch (_) {}
      render(ids);
    })
    .catch(() => {
      // Keep the last known sequence when the dashboard cannot be refreshed.
    })
    .finally(() => clearTimeout(timeout));
  window.addEventListener('pagehide', () => controller.abort());
})();
