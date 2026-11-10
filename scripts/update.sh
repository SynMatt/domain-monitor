#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/common.sh"
require_root "$@"; require_install
MODE=update; REQUESTED=''
case "${1:-}" in
  --check) MODE=check ;;
  --version) REQUESTED=${2:-}; [ -n "$REQUESTED" ] || { echo 'Missing version.'; exit 1; } ;;
  '') ;;
  *) echo "Usage: sudo $0 [--check | --version X.Y.Z]"; exit 1 ;;
esac

[ -d .git ] || { echo 'This updater requires an installation cloned from GitHub.'; exit 1; }
[ -z "$(git status --porcelain)" ] || { echo 'Tracked files have local changes. Update stopped.'; git status --short; exit 1; }
CURRENT=$(app_version)
git fetch --tags --prune origin
TARGET_TAG=${REQUESTED:+v$REQUESTED}
[ -n "$TARGET_TAG" ] || TARGET_TAG=$(semver_latest)
[ -n "$TARGET_TAG" ] || { echo 'No stable release tags found.'; exit 1; }
TARGET=${TARGET_TAG#v}
printf 'Current: %s\nLatest requested stable release: %s\n' "$CURRENT" "$TARGET"
[ "$MODE" = check ] && exit 0
[ "$CURRENT" != "$TARGET" ] || { echo 'Already up to date.'; exit 0; }
git rev-parse -q --verify "refs/tags/$TARGET_TAG" >/dev/null || { echo "Release not found: $TARGET_TAG"; exit 1; }

OLD_REF=$(git rev-parse HEAD)
OLD_IMAGE=$(compose images -q web)
DOMAINS=$(db_metric 'SELECT COUNT(*) FROM domains')
HISTORY=$(db_metric 'SELECT COUNT(*) FROM history')
BACKUP=$DM_BACKUPS/update-${CURRENT}-to-${TARGET}-$(date -u +%Y%m%dT%H%M%SZ)
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
# Runtime files remain ignored and are preserved across checkout.
export DOMAIN_MONITOR_VERSION=$TARGET
compose build --pull
for test in tests/test_*.py; do
  echo "Running $test"
  compose run --rm --no-deps -e PYTHONPATH=/app web python "/app/$test"
done
compose up -d --force-recreate --wait --wait-timeout 180
[ "$(running_version)" = "$TARGET" ]
integrity_check
[ "$(db_metric 'SELECT COUNT(*) FROM domains')" = "$DOMAINS" ]
[ "$(db_metric 'SELECT COUNT(*) FROM history')" -ge "$HISTORY" ]
trap - ERR
printf 'Update completed: %s -> %s\nBackup: %s\n' "$CURRENT" "$TARGET" "$BACKUP"
