#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

DM_ROOT=${DOMAIN_MONITOR_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
DM_BACKUPS=${DOMAIN_MONITOR_BACKUPS:-$DM_ROOT/backups}
DM_DATA=${DOMAIN_MONITOR_DATA:-$DM_ROOT/data}
DM_DB=$DM_DATA/monitor.sqlite3

require_root(){ [ "$(id -u)" -eq 0 ] || { echo "Run with sudo: sudo $0 $*"; exit 1; }; }
require_install(){
  cd "$DM_ROOT"
  [ -f compose.yaml ] && [ -f .env ] && [ -f app.py ] || { echo "Domain Monitor installation not found at $DM_ROOT"; exit 1; }
  [ -f "$DM_DB" ] || { echo "Database not found at $DM_DB"; exit 1; }
}
app_version(){ sed -n "s/^APP_VERSION='\([^']*\)'$/\1/p" "$DM_ROOT/app.py"; }
running_version(){ docker compose -f "$DM_ROOT/compose.yaml" --env-file "$DM_ROOT/.env" exec -T web python -c 'import app; print(app.APP_VERSION)' 2>/dev/null; }
db_metric(){
  local sql=$1
  docker compose -f "$DM_ROOT/compose.yaml" --env-file "$DM_ROOT/.env" exec -T web python - "$sql" <<'PY'
import sqlite3,sys
c=sqlite3.connect('/data/monitor.sqlite3')
print(c.execute(sys.argv[1]).fetchone()[0])
c.close()
PY
}
integrity_check(){ [ "$(db_metric 'PRAGMA integrity_check')" = ok ]; }
semver_latest(){ git tag -l 'v[0-9]*.[0-9]*.[0-9]*' --sort=-version:refname | head -n1; }
compose(){ docker compose -f "$DM_ROOT/compose.yaml" --env-file "$DM_ROOT/.env" "$@"; }
