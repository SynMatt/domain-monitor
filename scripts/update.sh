#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/common.sh"
require_root "$@"
require_install

MODE=update
REQUESTED=''
case "${1:-}" in
  --check) MODE=check ;;
  --version)
    REQUESTED=${2:-}
    [ -n "$REQUESTED" ] || { echo 'Missing version.'; exit 1; }
    ;;
  '') ;;
  *) echo "Usage: sudo $0 [--check | --version X.Y.Z]"; exit 1 ;;
esac

[ -d .git ] || { echo 'This updater requires an installation cloned from GitHub.'; exit 1; }
[ -z "$(git status --porcelain)" ] || { echo 'Tracked files have local changes. Update stopped.'; git status --short; exit 1; }

SOURCE_VERSION=$(app_version)
RUNNING_VERSION=$(running_version 2>/dev/null || true)
[ -n "$RUNNING_VERSION" ] || RUNNING_VERSION='not-running'

git fetch --tags --prune origin
TARGET_TAG=${REQUESTED:+v$REQUESTED}
[ -n "$TARGET_TAG" ] || TARGET_TAG=$(semver_latest)
[ -n "$TARGET_TAG" ] || { echo 'No stable release tags found.'; exit 1; }
TARGET=${TARGET_TAG#v}

echo "Source version:  $SOURCE_VERSION"
echo "Running version: $RUNNING_VERSION"
echo "Latest requested stable release: $TARGET"

if [ "$MODE" = check ]; then
  if [ "$SOURCE_VERSION" = "$TARGET" ] && [ "$RUNNING_VERSION" = "$TARGET" ]; then
    echo 'Status: up to date'
  elif [ "$SOURCE_VERSION" = "$TARGET" ] && [ "$RUNNING_VERSION" != "$TARGET" ]; then
    echo 'Status: source/container drift detected; run the updater to rebuild and recreate containers.'
  else
    echo "Status: update available to $TARGET"
  fi
  exit 0
fi

if [ "$SOURCE_VERSION" = "$TARGET" ] && [ "$RUNNING_VERSION" = "$TARGET" ]; then
  echo 'Already up to date.'
  exit 0
fi

git rev-parse -q --verify "refs/tags/$TARGET_TAG" >/dev/null || { echo "Release not found: $TARGET_TAG"; exit 1; }

# Preserve the currently published binding before any checkout. Values already
# stored in .env win; otherwise infer the active web binding from Docker.
PUBLISHED=$(compose port web 8080 2>/dev/null || true)
CURRENT_BIND_IP=${PUBLISHED%:*}
CURRENT_BIND_PORT=${PUBLISHED##*:}
[ "$CURRENT_BIND_IP" != "$PUBLISHED" ] || CURRENT_BIND_IP='127.0.0.1'
case "$CURRENT_BIND_PORT" in ''|*[!0-9]*) CURRENT_BIND_PORT='8282' ;; esac

OLD_REF=$(git rev-parse HEAD)
DOMAINS=$(db_metric 'SELECT COUNT(*) FROM domains')
HISTORY=$(db_metric 'SELECT COUNT(*) FROM history')
BACKUP=$DM_BACKUPS/update-${SOURCE_VERSION}-to-${TARGET}-$(date -u +%Y%m%dT%H%M%SZ)
"$DM_ROOT/scripts/backup.sh" "$BACKUP"

rollback(){
  echo 'UPDATE FAILED: rolling back source and runtime.' >&2
  compose stop web worker || true
  git checkout -f "$OLD_REF" || true
  cp -a "$BACKUP/environment.env" .env || true
  cp -a "$BACKUP/monitor.sqlite3" "$DM_DB.new" || true
  chmod 0600 "$DM_DB.new" 2>/dev/null || true
  chown +10001:+10001 "$DM_DB.new" 2>/dev/null || true
  mv -f "$DM_DB.new" "$DM_DB" 2>/dev/null || true
  compose build || true
  compose up -d --force-recreate --wait --wait-timeout 180 || true
  echo "Rollback backup: $BACKUP" >&2
}
trap rollback ERR

git checkout -f "$TARGET_TAG"

# Persist the image version and deployment-specific network binding in the
# untracked .env file. This prevents Compose falling back to :latest or
# localhost when containers are recreated.
python3 - "$TARGET" "$CURRENT_BIND_IP" "$CURRENT_BIND_PORT" <<'PY'
from pathlib import Path
import sys
version, bind_ip, bind_port = sys.argv[1:4]
path = Path('.env')
lines = path.read_text().splitlines()
keys = {'DOMAIN_MONITOR_VERSION', 'HOST_BIND_IP', 'HOST_PORT'}
lines = [line for line in lines if line.split('=', 1)[0] not in keys]
lines.extend([
    f"DOMAIN_MONITOR_VERSION='{version}'",
    f"HOST_BIND_IP='{bind_ip}'",
    f"HOST_PORT='{bind_port}'",
])
path.write_text('\n'.join(lines) + '\n')
path.chmod(0o600)
PY

compose config --quiet
compose build --pull
for test in tests/test_*.py; do
  echo "Running $test"
  compose run --rm --no-deps -e PYTHONPATH=/app web python "/app/$test"
done
compose up -d --force-recreate --wait --wait-timeout 180

[ "$(running_version)" = "$TARGET" ]
[ "$(compose config --images | sort -u)" = "domain-monitor:$TARGET" ]
[ "$(compose port web 8080)" = "$CURRENT_BIND_IP:$CURRENT_BIND_PORT" ]
integrity_check
[ "$(db_metric 'SELECT COUNT(*) FROM domains')" = "$DOMAINS" ]
[ "$(db_metric 'SELECT COUNT(*) FROM history')" -ge "$HISTORY" ]
trap - ERR

printf 'Update completed: source %s, running %s -> %s\n' "$SOURCE_VERSION" "$RUNNING_VERSION" "$TARGET"
printf 'Binding preserved: %s:%s\nBackup: %s\n' "$CURRENT_BIND_IP" "$CURRENT_BIND_PORT" "$BACKUP"
