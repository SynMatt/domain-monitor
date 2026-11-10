#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/common.sh"
require_root "$@"; require_install
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
DEST=${1:-$DM_BACKUPS/manual-$STAMP}
install -d -m 0700 "$DEST"
[ ! -e "$DEST/monitor.sqlite3" ] || { echo "Backup already exists: $DEST"; exit 1; }
cp -a .env "$DEST/environment.env"; chmod 0600 "$DEST/environment.env"
cp -a compose.yaml "$DEST/compose.yaml"
[ ! -f compose.override.yaml ] || cp -a compose.override.yaml "$DEST/compose.override.yaml"
printf '%s\n' "$(app_version)" > "$DEST/source-version.txt"
python3 - "$DM_DB" "$DEST/monitor.sqlite3" <<'PY'
import sqlite3,sys
source_path,destination_path=sys.argv[1:3]
source=sqlite3.connect(f'file:{source_path}?mode=ro',uri=True)
target=sqlite3.connect(destination_path)
source.backup(target)
result=target.execute('PRAGMA integrity_check').fetchone()[0]
target.close(); source.close()
if result!='ok': raise SystemExit(f'Backup integrity check failed: {result}')
print('Backup database integrity: ok')
PY
chmod 0600 "$DEST/monitor.sqlite3"
DOMAINS=$(db_metric 'SELECT COUNT(*) FROM domains')
HISTORY=$(db_metric 'SELECT COUNT(*) FROM history')
cat > "$DEST/manifest.txt" <<EOF
created_utc=$STAMP
version=$(app_version)
domains=$DOMAINS
history=$HISTORY
EOF
chmod 0600 "$DEST/manifest.txt" "$DEST/source-version.txt"
echo "Backup completed: $DEST"
