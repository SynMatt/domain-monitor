#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/common.sh"
require_root "$@"; require_install
BACKUP=${1:-}
[ -n "$BACKUP" ] || { echo "Usage: sudo $0 /path/to/backup"; exit 1; }
[ -f "$BACKUP/monitor.sqlite3" ] && [ -f "$BACKUP/environment.env" ] || { echo 'Invalid backup directory.'; exit 1; }
python3 - "$BACKUP/monitor.sqlite3" <<'PY'
import sqlite3,sys
c=sqlite3.connect(sys.argv[1]); result=c.execute('PRAGMA integrity_check').fetchone()[0]; c.close()
assert result=='ok',result
print('Backup database integrity: ok')
PY
SAFETY=$DM_BACKUPS/pre-restore-$(date -u +%Y%m%dT%H%M%SZ)
"$DM_ROOT/scripts/backup.sh" "$SAFETY"
compose stop web worker
cp -a "$BACKUP/environment.env" .env; chmod 0600 .env
install -m 0600 -o 10001 -g 10001 "$BACKUP/monitor.sqlite3" "$DM_DB.new"
mv -f "$DM_DB.new" "$DM_DB"
if ! compose up -d --force-recreate --wait --wait-timeout 180; then
  echo "Restore start failed. Safety backup retained at $SAFETY"
  exit 1
fi
integrity_check || { echo 'Restored database integrity failed.'; exit 1; }
echo "Restore completed. Pre-restore safety backup: $SAFETY"
