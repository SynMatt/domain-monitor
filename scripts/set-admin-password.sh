#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

ROOT=${DOMAIN_MONITOR_ROOT:-/opt/domain-monitor}
cd "$ROOT"

[ -f compose.yaml ] && [ -f .env ] || {
    echo "Domain Monitor installation not found at $ROOT."
    exit 1
}

TMP_HASH=$(mktemp)
BACKUP=".env.backup-$(date +%Y%m%d-%H%M%S)"
cleanup() {
    rm -f "$TMP_HASH"
    unset NEW_PASSWORD CONFIRM_PASSWORD PASSWORD_HASH SECRET_KEY
}
trap cleanup EXIT

printf '%s\n' 'Enter the Domain Monitor administrator password.'
printf '%s\n' 'Nothing will appear while typing.'
printf '\n'
read -r -s -p 'Administrator password: ' NEW_PASSWORD
printf '\n'
read -r -s -p 'Confirm password: ' CONFIRM_PASSWORD
printf '\n'

[ "$NEW_PASSWORD" = "$CONFIRM_PASSWORD" ] || {
    echo 'ERROR: The passwords do not match.'
    exit 1
}
[ "${#NEW_PASSWORD}" -ge 12 ] || {
    echo 'ERROR: The password must contain at least 12 characters.'
    exit 1
}

cp -a .env "$BACKUP"
chmod 0600 "$BACKUP"

printf '%s\n' "$NEW_PASSWORD" |
docker compose run --rm --no-deps -T --entrypoint python web -c '
import sys
from werkzeug.security import generate_password_hash
password = sys.stdin.readline().rstrip("\n")
print(generate_password_hash(password))
' > "$TMP_HASH"

if ! grep -Eq '^(scrypt:|pbkdf2:)' "$TMP_HASH"; then
    echo 'ERROR: A valid Werkzeug password hash was not generated.'
    exit 1
fi

SECRET_KEY=$(sed -n 's/^SECRET_KEY=//p' .env | head -n 1 | sed "s/^'//;s/'$//")
if [ -z "$SECRET_KEY" ]; then
    echo 'The existing session key is missing; generating a replacement.'
    SECRET_KEY=$(openssl rand -hex 32)
fi
PASSWORD_HASH=$(cat "$TMP_HASH")

cat > .env.new <<EOF
SECRET_KEY='$SECRET_KEY'
ADMIN_PASSWORD_HASH='$PASSWORD_HASH'
EOF
chmod 0600 .env.new
mv -f .env.new .env

if ! docker compose config --quiet; then
    echo 'Compose validation failed. Restoring the previous environment file.'
    cp -a "$BACKUP" .env
    exit 1
fi

if ! docker compose up -d --force-recreate --wait --wait-timeout 180 web worker; then
    echo 'Container recreation failed. Restoring the previous environment file.'
    cp -a "$BACKUP" .env
    docker compose up -d --force-recreate web worker
    exit 1
fi

VERIFY_RESULT=$(
    printf '%s\n' "$NEW_PASSWORD" |
    docker compose exec -T web python -c '
import os
import sys
from werkzeug.security import check_password_hash
password = sys.stdin.readline().rstrip("\n")
stored_hash = os.environ.get("ADMIN_PASSWORD_HASH", "")
print("PASS" if stored_hash and check_password_hash(stored_hash, password) else "FAIL")
'
)

if [ "$VERIFY_RESULT" != PASS ]; then
    echo 'ERROR: The running web container did not accept the password.'
    echo 'Restoring the previous environment file and containers.'
    cp -a "$BACKUP" .env
    docker compose up -d --force-recreate --wait --wait-timeout 180 web worker
    exit 1
fi

unset NEW_PASSWORD CONFIRM_PASSWORD PASSWORD_HASH SECRET_KEY
printf '\nPASSWORD RESET AND VERIFIED SUCCESSFULLY\n'
printf 'Environment backup: %s/%s\n' "$ROOT" "$BACKUP"
docker compose ps
