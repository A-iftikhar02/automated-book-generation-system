#!/usr/bin/env bash
# Restore a backup made by scripts/backup.sh. REPLACES the books currently in this installation.
#
# Usage:  ./scripts/restore.sh path/to/bookpilot-backup-XXXX.tar.gz [--yes]
# Run it from the project folder after `docker compose up -d --build` has been run once on this machine.
set -euo pipefail
cd "$(dirname "$0")/.."

ARCHIVE=""
YES=false
for arg in "$@"; do
  case "$arg" in
    --yes|-y) YES=true ;;
    -h|--help) sed -n '2,5p' "$0"; exit 0 ;;
    *) ARCHIVE="$arg" ;;
  esac
done
[ -n "$ARCHIVE" ] && [ -f "$ARCHIVE" ] || { echo "Usage: $0 path/to/backup.tar.gz [--yes]"; exit 1; }

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
tar -C "$WORK" -xzf "$ARCHIVE"
[ -f "$WORK/database.dump" ] || { echo "Not a BookPilot backup (database.dump missing)."; exit 1; }
cat "$WORK/manifest.txt" 2>/dev/null || true
echo

if ! $YES; then
  read -r -p "This replaces all books in this installation with the backup. Continue? [y/N] " answer
  [[ "$answer" =~ ^[Yy]$ ]] || { echo "Cancelled."; exit 0; }
fi

if [ -f "$WORK/env" ]; then
  if [ -f .env ]; then
    cp "$WORK/env" .env.from-backup
    echo "The backup contains a .env; saved it as .env.from-backup (your existing .env was left untouched)."
  else
    cp "$WORK/env" .env
    echo "Restored .env from the backup."
  fi
fi

echo "Building images (needed for the storage volume)…"
docker compose build api >/dev/null
docker compose up -d db
for _ in $(seq 1 60); do
  docker compose exec -T db pg_isready -U bookpilot -d bookpilot >/dev/null 2>&1 && break
  sleep 1
done
echo "Stopping the API and worker during the restore…"
docker compose stop api worker frontend >/dev/null 2>&1 || true

echo "Restoring database…"
docker compose exec -T db psql -U bookpilot -d postgres -q -c "DROP DATABASE IF EXISTS bookpilot WITH (FORCE)" -c "CREATE DATABASE bookpilot OWNER bookpilot"
docker compose exec -T db pg_restore -U bookpilot -d bookpilot --no-owner --no-acl --exit-on-error < "$WORK/database.dump"

echo "Restoring covers and exports…"
docker compose run --rm --no-deps -T -v "$WORK":/backup:ro --entrypoint sh api \
  -c 'rm -rf /data/storage/* && tar -xzf /backup/storage.tar.gz -C /data/storage'
# Also restore into ./storage for people running the API directly on the host (not in Docker).
mkdir -p storage && tar -xzf "$WORK/storage.tar.gz" -C storage

echo "Starting BookPilot (database migrations run automatically)…"
docker compose up -d
BOOKS=$(docker compose exec -T db psql -U bookpilot -d bookpilot -At -c "select count(*) from books" | tr -d '\r')
echo "Done: $BOOKS books restored. Open http://localhost:3000"
