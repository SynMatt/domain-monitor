#!/usr/bin/env bash
# Remove old Domain Monitor Docker images safely.
# Keeps: images used by any container, the configured release, and the 2 newest
# older releases for rollback. Removes old release tags, candidate/verification
# tags and leftover update tags. Previews first and asks for confirmation.
# Usage: sudo ./scripts/cleanup-images.sh [--yes]
set -Eeuo pipefail
cd "$(dirname "$0")/.."
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo: sudo ./scripts/cleanup-images.sh"; exit 1; }

KEEP_OLDER=2
CURRENT=$(sed -n "s/^DOMAIN_MONITOR_VERSION='\{0,1\}\([^']*\)'\{0,1\}$/\1/p" .env 2>/dev/null | tail -n 1)
[ -n "$CURRENT" ] || CURRENT=$(sed -n "s/^APP_VERSION='\([^']*\)'$/\1/p" app.py)
[ -n "$CURRENT" ] || { echo "STOP: Could not determine the current version."; exit 1; }

USED_IDS=$(docker ps -aq | xargs -r docker inspect --format '{{.Image}}')

mapfile -t RELEASES < <(
  docker image ls 'domain-monitor' --format '{{.Tag}}' |
  grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' | sort -V
)

KEEP=("$CURRENT")
older=()
for tag in "${RELEASES[@]}"; do
  [ "$(printf '%s\n%s\n' "$tag" "$CURRENT" | sort -V | tail -n1)" = "$CURRENT" ] &&
    [ "$tag" != "$CURRENT" ] && older+=("$tag")
done
for ((i=${#older[@]}-1, n=0; i>=0 && n<KEEP_OLDER; i--, n++)); do KEEP+=("${older[$i]}"); done

REMOVE=()
while IFS= read -r tag; do
  [ "$tag" = "<none>" ] && continue
  ref="domain-monitor:$tag"
  printf '%s\n' "${KEEP[@]}" | grep -Fxq "$tag" && continue
  id=$(docker image inspect --format '{{.Id}}' "$ref")
  if grep -Fxq "$id" <<< "$USED_IDS"; then
    echo "Keeping (used by a container): $ref"; continue
  fi
  REMOVE+=("$ref")
done < <(docker image ls 'domain-monitor' --format '{{.Tag}}')

echo
echo "Current release: $CURRENT"
echo "Keeping releases: ${KEEP[*]}"
echo
if [ "${#REMOVE[@]}" -eq 0 ]; then
  echo "Nothing to remove."
  exit 0
fi
echo "Image tags to remove:"
printf '  %s\n' "${REMOVE[@]}"
echo
if [ "${1:-}" != "--yes" ]; then
  read -r -p "Type CLEANUP to remove these image tags: " answer < /dev/tty
  [ "$answer" = "CLEANUP" ] || { echo "Cancelled. Nothing removed."; exit 0; }
fi
for ref in "${REMOVE[@]}"; do
  docker image rm "$ref" >/dev/null && echo "Removed $ref" || echo "Skipped $ref (Docker refused)"
done
echo
docker system df
echo "Cleanup complete. Containers, volumes, data and backups were not touched."
