(() => {
  'use strict';
  const nav = document.getElementById('domain-sequence-nav');
  if (!nav || !/^\d+$/.test(nav.dataset.domainId)) return;
  let saved;
  try { saved = JSON.parse(sessionStorage.getItem('domain-monitor-dashboard-view')); } catch (_) { return; }
  if (!saved || typeof saved.href !== 'string' || !Array.isArray(saved.ids)) return;
  let url;
  try { url = new URL(saved.href, window.location.origin); } catch (_) { return; }
  if (url.origin !== window.location.origin || url.pathname !== '/' || url.hash) return;
  const ids = [...new Set(saved.ids.filter(id => /^\d+$/.test(String(id))).slice(0, 1000).map(String))];
  const current = ids.indexOf(nav.dataset.domainId);
  if (current < 0 || ids.length < 2) return;
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
  setLink(previous, ids[current - 1]);
  setLink(next, ids[current + 1]);
  position.textContent = (current + 1) + ' of ' + ids.length + ' in saved dashboard view';
  nav.hidden = false;
})();
