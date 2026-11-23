(() => {
  'use strict';

  if (window.location.pathname !== '/') return;

  const forms = [
    ...document.querySelectorAll(
      'form.domain-check-form[data-pending="1"]'
    )
  ];

  if (!forms.length) return;

  const ids = forms
    .map((form) => form.dataset.domainId)
    .filter((id) => /^\d+$/.test(id))
    .slice(0, 200);

  if (!ids.length) return;

  const positionKey = 'domain-monitor-dashboard-position';
  const dashboardControls = document.querySelector(
    'form.dashboard-controls'
  );

  let busy = false;
  let stopped = false;
  let refreshDeferred = false;
  let initialControls = '';

  if (dashboardControls) {
    initialControls = new URLSearchParams(
      new FormData(dashboardControls)
    ).toString();
  }

  function batchActive() {
    const panel = document.getElementById(
      'global-check-progress'
    );

    return Boolean(panel && !panel.hidden);
  }

  function controlsChanged() {
    if (!dashboardControls) return false;

    const currentControls = new URLSearchParams(
      new FormData(dashboardControls)
    ).toString();

    return currentControls !== initialControls;
  }

  function controlsInUse() {
    if (!dashboardControls) return false;

    const active = document.activeElement;

    return Boolean(
      active &&
      dashboardControls.contains(active) &&
      (
        active.matches('input, select, textarea, button') ||
        active.isContentEditable
      )
    );
  }

  function userIsInteracting() {
    return controlsInUse() || controlsChanged();
  }

  function reloadDashboard() {
    if (stopped || batchActive() || userIsInteracting()) {
      refreshDeferred = true;
      return;
    }

    stopped = true;
    refreshDeferred = false;

    sessionStorage.setItem(
      positionKey,
      JSON.stringify({
        href: window.location.pathname + window.location.search,
        y: window.scrollY,
        domainId: '',
        reason: 'auto-update',
        savedAt: Date.now()
      })
    );

    window.location.reload();
  }

  function tryDeferredReload() {
    if (!refreshDeferred) return;
    if (batchActive()) return;
    if (userIsInteracting()) return;

    reloadDashboard();
  }

  async function poll() {
    if (busy || stopped) return;

    busy = true;

    try {
      const response = await fetch(
        '/domains/status?ids=' +
          encodeURIComponent(ids.join(',')),
        {
          credentials: 'same-origin',
          cache: 'no-store'
        }
      );

      if (!response.ok) return;

      const data = (await response.json()).domains || {};
      let finished = false;

      for (const form of forms) {
        const item = data[form.dataset.domainId];
        const button = form.querySelector('button');

        if (!item || !button) continue;

        if (item.pending) {
          button.textContent = item.checking
            ? 'Checking\u2026'
            : 'Check queued';
          continue;
        }

        if (form.dataset.pending === '1') {
          form.dataset.pending = '0';
          finished = true;

          button.disabled = false;
          button.textContent = batchActive()
            ? 'Updated - refresh to view'
            : 'Updated';
        }
      }

      if (finished) {
        reloadDashboard();
      } else {
        tryDeferredReload();
      }
    } catch (error) {
      // A temporary polling failure must not interrupt the page.
    } finally {
      busy = false;
    }
  }

  if (dashboardControls) {
    dashboardControls.addEventListener(
      'focusout',
      () => {
        window.setTimeout(tryDeferredReload, 0);
      }
    );

    dashboardControls.addEventListener(
      'change',
      tryDeferredReload
    );

    dashboardControls.addEventListener(
      'submit',
      () => {
        stopped = true;
        refreshDeferred = false;
      }
    );

    const search = dashboardControls.querySelector('#q');

    if (search) {
      search.addEventListener(
        'input',
        () => {
          if (refreshDeferred) {
            search.setAttribute(
              'data-refresh-waiting',
              'true'
            );
          }
        }
      );
    }
  }

  document.addEventListener(
    'domain-monitor:check-all-complete',
    () => {
      if (refreshDeferred) {
        tryDeferredReload();
      }
    }
  );

  poll();
  window.setInterval(poll, 3000);
})();
