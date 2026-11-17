#!/usr/bin/env bash
# Domain Monitor Check-all performance monitor (read-only).
# Usage: sudo ./scripts/monitor-check-all.sh [samples] [seconds-between-samples]
# Start "Check all domains" first, then run this straight away.
set -u
SAMPLES=${1:-12}
INTERVAL=${2:-15}
cd "$(dirname "$0")/.." || exit 1

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo: sudo ./scripts/monitor-check-all.sh"; exit 1; }
WORKER_ID=$(docker compose ps -q worker)
[ -n "$WORKER_ID" ] || { echo "Worker container is not running."; exit 1; }

echo "=== Host and limits ==="
echo "Host CPU cores: $(nproc)"
docker inspect -f '{{.HostConfig.NanoCpus}} {{.HostConfig.Memory}}' "$WORKER_ID" |
  awk '{ printf "Worker CPU limit: %s cores | Memory limit: %s MiB\n", ($1==0?"none":$1/1e9), ($2==0?"none":$2/1048576) }'
docker compose exec -T worker python -c 'import app; print("Check workers:", app.check_workers())' </dev/null

echo
echo "=== Live samples: $SAMPLES x every ${INTERVAL}s ==="
for i in $(seq 1 "$SAMPLES"); do
  printf '\n--- %s ---\n' "$(date +%H:%M:%S)"
  docker stats --no-stream --format 'CPU {{.CPUPerc}} | Mem {{.MemUsage}}' "$WORKER_ID"
  docker compose exec -T web python - </dev/null <<'PY'
import sqlite3
c = sqlite3.connect("file:/data/monitor.sqlite3?mode=ro", uri=True)
b = c.execute("SELECT id, status, total FROM check_batches ORDER BY id DESC LIMIT 1").fetchone()
if not b:
    print("No Check-all batch found.")
else:
    n = dict(c.execute("SELECT status, COUNT(*) FROM check_batch_items WHERE batch_id=? GROUP BY status", (b[0],)).fetchall())
    print("Batch", b[0], "(" + b[1] + "): complete", n.get("complete", 0), "/", b[2],
          "| running", n.get("running", 0), "| queued", n.get("queued", 0), "| failed", n.get("failed", 0))
    if b[1] != "active":
        print("Batch is not running. Stopping samples.")
        raise SystemExit(3)
PY
  [ $? -eq 3 ] && break
  [ "$i" -lt "$SAMPLES" ] && sleep "$INTERVAL"
done

echo
echo "=== Latest batch summary ==="
docker compose exec -T web python - </dev/null <<'PY'
import sqlite3, statistics, time
c = sqlite3.connect("file:/data/monitor.sqlite3?mode=ro", uri=True)
c.row_factory = sqlite3.Row
b = c.execute("SELECT * FROM check_batches ORDER BY id DESC LIMIT 1").fetchone()
if not b:
    raise SystemExit("No batch found.")
rows = c.execute("""SELECT d.domain, i.started, i.finished FROM check_batch_items i
    JOIN domains d ON d.id = i.domain_id
    WHERE i.batch_id=? AND i.status='complete' AND i.started IS NOT NULL AND i.finished IS NOT NULL""",
    (b["id"],)).fetchall()
if not rows:
    raise SystemExit("No completed checks yet. Run again in a minute.")
secs = sorted(r["finished"] - r["started"] for r in rows)
first = min(r["started"] for r in rows)
last = max(r["finished"] for r in rows)
span = last - first
elapsed = (b["finished"] or time.time()) - b["created"]
rate = len(rows) / elapsed * 60 if elapsed else 0
print(f"Batch {b['id']} ({b['status']}): {len(rows)} / {b['total']} complete in {elapsed/60:.1f} min ({rate:.1f} domains/min)")
print(f"Seconds per domain: average {statistics.mean(secs):.1f} | median {statistics.median(secs):.1f} | slowest {secs[-1]:.1f}")
if span > 0:
    print(f"Domains checked at once (average): {sum(secs)/span:.1f}")
remaining = b["total"] - len(rows)
if b["status"] == "active" and rate and remaining > 0:
    print(f"Estimated time left: {remaining/rate:.1f} min")
print("\nSlowest 10 domains:")
for r in sorted(rows, key=lambda r: r["finished"] - r["started"], reverse=True)[:10]:
    print(f"  {r['finished'] - r['started']:6.1f}s  {r['domain']}")
PY

echo
echo "=== Real check timing for the 3 slowest domains (one process each, results NOT saved) ==="
docker compose exec -T worker python - </dev/null <<'PY'
import sqlite3, subprocess, sys, time
c = sqlite3.connect("file:/data/monitor.sqlite3?mode=ro", uri=True)
c.row_factory = sqlite3.Row
b = c.execute("SELECT id FROM check_batches ORDER BY id DESC LIMIT 1").fetchone()
if not b:
    raise SystemExit("No batch found.")
rows = c.execute("""SELECT d.domain, d.selectors, d.policy FROM check_batch_items i
    JOIN domains d ON d.id = i.domain_id
    WHERE i.batch_id=? AND i.started IS NOT NULL AND i.finished IS NOT NULL
    ORDER BY i.finished - i.started DESC LIMIT 3""", (b["id"],)).fetchall()
for r in rows:
    t = time.perf_counter()
    p = subprocess.run([sys.executable, "app.py", "check-domain", r["domain"], r["selectors"] or "", r["policy"], "0"],
                       capture_output=True, text=True, timeout=300)
    outcome = "ok" if p.returncode == 0 else f"exit {p.returncode}"
    print(f"  {time.perf_counter() - t:6.2f}s  {r['domain']}  ({outcome}; expiry skipped)")
PY

echo
echo "=== MONITOR COMPLETE (nothing was changed) ==="
