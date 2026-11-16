(() => {
 const panel=document.getElementById('check-progress'); if(!panel)return;
 const title=document.getElementById('check-progress-title'),bar=document.getElementById('check-progress-bar'),detail=document.getElementById('check-progress-detail'),button=document.querySelector('form[action="/check-all"] button');
 async function poll(){try{const r=await fetch('/check-all/status',{credentials:'same-origin',cache:'no-store'});if(!r.ok)return;const d=await r.json(),active=d.status==='active'||d.status==='stalled';panel.hidden=!active;if(active){title.textContent=d.status==='stalled'?'Check-all appears stalled':`Checking all domains: ${d.done} / ${d.total} complete`;bar.value=d.percent||0;detail.textContent=`${d.queued} queued · ${d.running} checking · ${d.failed} failed · ${d.workers || 1} workers${d.eta_seconds == null ? '' : ' · about ' + Math.max(1, Math.ceil(d.eta_seconds / 60)) + ' min remaining'}`;if(button){button.disabled=true;button.textContent=`Checking ${d.done} / ${d.total}...`;}}else if(button){button.disabled=false;button.textContent='Check all domains';}}catch(e){}}
 poll();setInterval(poll,3000);
})();
