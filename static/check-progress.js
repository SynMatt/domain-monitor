(() => {
  "use strict";

  const panel = document.getElementById("global-check-progress");
  if (!panel) return;

  const title = document.getElementById("check-progress-title");
  const bar = document.getElementById("check-progress-bar");
  const detail = document.getElementById("check-progress-detail");
  const cancel = document.getElementById("cancel-check-all");
  const checkAllForms = Array.from(
    document.querySelectorAll('form[action="/check-all"]')
  );
  const checkAllButtons = checkAllForms
    .map((form) => form.querySelector("button"))
    .filter(Boolean);

  let timer = null;
  let previouslyActive = false;

  function setCheckAllButtons(active, done, total) {
    for (const button of checkAllButtons) {
      button.disabled = active;
      button.textContent = active
        ? `Checking ${done} / ${total}...`
        : "Check all domains";
    }
  }

  function scheduleNextPoll(delay = 3000) {
    window.clearTimeout(timer);
    timer = window.setTimeout(poll, delay);
  }

  async function poll() {
    try {
      const response = await fetch("/check-all/status", {
        credentials: "same-origin",
        cache: "no-store",
        headers: {
          Accept: "application/json"
        }
      });

      if (!response.ok) {
        scheduleNextPoll(5000);
        return;
      }

      const data = await response.json();
      const active =
        data.status === "active" || data.status === "stalled";

      if (!active) {
        panel.hidden = true;
        cancel.hidden = true;
        setCheckAllButtons(false, 0, 0);

        if (previouslyActive) {
          document.dispatchEvent(
            new CustomEvent("domain-monitor:check-all-complete", {
              detail: data
            })
          );
        }

        previouslyActive = false;
        scheduleNextPoll(3000);
        return;
      }

      previouslyActive = true;
      panel.hidden = false;
      cancel.hidden = false;

      const done = Number.isFinite(Number(data.done))
        ? Number(data.done)
        : 0;
      const total = Number.isFinite(Number(data.total))
        ? Number(data.total)
        : 0;
      const queued = Number.isFinite(Number(data.queued))
        ? Number(data.queued)
        : 0;
      const running = Number.isFinite(Number(data.running))
        ? Number(data.running)
        : 0;
      const failed = Number.isFinite(Number(data.failed))
        ? Number(data.failed)
        : 0;
      const workers = Number.isFinite(Number(data.workers))
        ? Number(data.workers)
        : 1;
      const percent = Math.max(
        0,
        Math.min(100, Number(data.percent) || 0)
      );

      title.textContent =
        data.status === "stalled"
          ? `Check all appears stalled: ${done} / ${total} complete`
          : `Checking all domains: ${done} / ${total} complete`;

      bar.value = percent;
      bar.textContent = `${percent}%`;
      bar.setAttribute("aria-valuenow", String(percent));

      const details = [
        `${queued} queued`,
        `${running} checking`,
        `${failed} failed`,
        `${workers} worker${workers === 1 ? "" : "s"}`
      ];

      if (data.avg_seconds != null) {
        details.push(`${data.avg_seconds}s per domain`);
      }

      if (data.eta_seconds != null) {
        const minutes = Math.max(
          1,
          Math.ceil(Number(data.eta_seconds) / 60)
        );
        details.push(`about ${minutes} min remaining`);
      }

      detail.textContent = details.join(" · ");
      setCheckAllButtons(true, done, total);
      scheduleNextPoll(3000);
    } catch (error) {
      scheduleNextPoll(5000);
    }
  }

  for (const form of checkAllForms) {
    form.addEventListener("submit", () => {
      panel.hidden = false;
      cancel.hidden = true;
      title.textContent = "Starting Check all...";
      detail.textContent = "Preparing domain checks...";
      bar.value = 0;
      setCheckAllButtons(true, 0, 0);
      scheduleNextPoll(1000);
    });
  }

  poll();
})();
