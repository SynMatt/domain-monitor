#!/usr/bin/env bash
# Build a candidate image from this checkout and run the whole test suite once.
# Usage: ./scripts/run-tests.sh [name-filter]   e.g. ./scripts/run-tests.sh history
# Uses Docker's build cache, a read-only container and a temporary /tmp, like production.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
SUDO=''; [ "$(id -u)" -eq 0 ] || SUDO='sudo'
VERSION=$(sed -n "s/^APP_VERSION='\([^']*\)'$/\1/p" app.py)
TAG="domain-monitor:test-$VERSION"
ARGS=(-m unittest discover -s /app/tests -t /app/tests)
[ -z "${1:-}" ] || ARGS+=(-k "$1")
START=$(date +%s)
echo "Building $TAG ..."
$SUDO docker build -q -t "$TAG" . >/dev/null
BUILT=$(date +%s)
echo "Running tests ..."
$SUDO docker run --rm --read-only --tmpfs /tmp:rw,noexec,nosuid,size=128m \
  -e PYTHONPATH=/app:/app/tests "$TAG" python "${ARGS[@]}"
END=$(date +%s)
echo "Build: $((BUILT-START))s | Tests: $((END-BUILT))s | Image: $TAG"
