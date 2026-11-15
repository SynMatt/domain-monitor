(() => {
  'use strict';
  if (window.location.pathname !== '/') return;
  const key = 'domain-monitor-dashboard-position';
  if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
  const raw = sessionStorage.getItem(key);
  if (raw) {
    sessionStorage.removeItem(key);
    try {
      const saved = JSON.parse(raw);
      if (saved.href === location.pathname + location.search) {
        requestAnimationFrame(() => requestAnimationFrame(() => {
          const form = Array.from(document.querySelectorAll('form.domain-check-form')).find(x => x.dataset.domainId === String(saved.domainId));
          const card = form && form.closest('article.card');
          if (card) card.scrollIntoView({block:'center',inline:'nearest'});
          else if (Number.isFinite(saved.y)) scrollTo({top:Math.max(0,saved.y),left:0,behavior:'auto'});
        }));
      }
    } catch (_) {}
  }
  document.addEventListener('submit', event => {
    const form = event.target.closest('form.domain-check-form');
    if (!form) return;
    const button = form.querySelector('button');
    if (button) { button.disabled = true; button.textContent = 'Check queued'; }
    sessionStorage.setItem(key, JSON.stringify({href:location.pathname+location.search,y:scrollY,domainId:form.dataset.domainId||''}));
  });
})();
