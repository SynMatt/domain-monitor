#!/usr/bin/env bash
# Set CONTAINER_CPUS and CHECK_WORKERS in .env to suit this host.
# Usage: sudo ./scripts/tune-resources.sh [--dry-run] [--no-restart]
#   --dry-run     show what would change; change nothing
#   --no-restart  update .env only (used by set-admin-password.sh and update.sh)
# Running containers are recreated when a value changes, unless --no-restart.
set -Eeuo pipefail
ROOT=${DOMAIN_MONITOR_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
cd "$ROOT"
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo: sudo ./scripts/tune-resources.sh"; exit 1; }
[ -f .env ] || { echo "No .env in $ROOT. Run: cp .env.example .env && chmod 600 .env"; exit 1; }
DRY=(); RESTART=1
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=(--dry-run) ;;
    --no-restart) RESTART=0 ;;
    *) echo "Usage: sudo $0 [--dry-run] [--no-restart]"; exit 1 ;;
  esac
done
# Ask Docker first: its CPU and memory view is the one it enforces limits against.
CPUS=$(docker info --format '{{.NCPU}}' 2>/dev/null || true)
MEM=$(docker info --format '{{.MemTotal}}' 2>/dev/null || true)
case "$CPUS" in ''|*[!0-9]*|0) CPUS=$(nproc) ;; esac
case "$MEM" in ''|*[!0-9]*|0) MEM=$(awk '/^MemTotal:/{printf "%d", $2*1024}' /proc/meminfo) ;; esac
# Hyper-V Dynamic Memory makes the guest's memory reading unreliable, so ignore it there.
HYPERV=()
if [ -d /sys/module/hv_balloon ] || [ "$(systemd-detect-virt 2>/dev/null || true)" = microsoft ]; then
  HYPERV=(--ignore-memory)
fi
echo "=== Resource tuning ==="
set +e
python3 "$ROOT/scripts/tune_resources.py" --env .env --cpus "$CPUS" --mem "$MEM" "${DRY[@]}" "${HYPERV[@]}"
STATUS=$?
set -e
[ "$STATUS" -eq 0 ] && exit 0
[ "$STATUS" -eq 3 ] || exit "$STATUS"
if [ "$RESTART" -eq 1 ] && [ -n "$(docker compose ps -q 2>/dev/null)" ]; then
  echo "Recreating containers with the new limits ..."
  docker compose up -d --force-recreate --wait --wait-timeout 180
fi
exit 0
