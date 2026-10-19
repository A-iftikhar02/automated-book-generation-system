#!/usr/bin/env bash
# Back up everything BookPilot needs to continue on another machine into ONE file:
#   database.dump   - all books, outlines, chapters, revisions, QA results, jobs (pg_dump, custom format)
#   storage.tar.gz  - covers, cover art and exported files (Docker volume + local ./storage if present)
#   env             - your .env (API keys) ONLY when run with --with-env
#   manifest.txt    - what's inside and where it came from
#
# Usage:  ./scripts/backup.sh [--with-env] [output-file]
# Default output: backups/bookpilot-backup-<date>.tar.gz
set -euo pipefail
cd "$(dirname "$0")/.."
PROJECT=${COMPOSE_PROJECT_NAME:-bookpilot}  # matches `name:` in docker-compose.yml
VOLUME="${PROJECT}_storage"

WITH_ENV=false
OUT=""
for arg in "$@"; do
  case "$arg" in
    --with-env) WITH_ENV=true ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) OUT="$arg" ;;
  esac
done
STAMP=$(date +%Y%m%d-%H%M%S)
OUT=${OUT:-backups/bookpilot-backup-$STAMP.tar.gz}
mkdir -p "$(dirname "$OUT")"

if ! docker compose ps --status running --services 2>/dev/null | grep -qx db; then
  echo "Starting the database container…"
  docker compose up -d db
fi
for _ in $(seq 1 30); do
  docker compose exec -T db pg_isready -U bookpilot -d bookpilot >/dev/null 2>&1 && break
  sleep 1
done

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/backup" "$WORK/storage"

echo "Dumping database…"
docker compose exec -T db pg_dump -U bookpilot -d bookpilot --format=custom --no-owner --no-acl > "$WORK/backup/database.dump"

echo "Collecting covers and exports…"
# Local runs (uvicorn on the host) keep files in ./storage; Docker keeps them in the <project>_storage volume.
if [ -d storage ]; then
  cp -R storage/. "$WORK/storage/"
fi
if docker volume inspect "$VOLUME" >/dev/null 2>&1; then
  docker compose run --rm --no-deps -T -v "$WORK/storage":/out --entrypoint sh api \
    -c 'cp -R /data/storage/. /out/ 2>/dev/null || true'
fi
COPYFILE_DISABLE=1 tar --no-xattrs -C "$WORK/storage" -czf "$WORK/backup/storage.tar.gz" .

if $WITH_ENV && [ -f .env ]; then
  cp .env "$WORK/backup/env"
  echo "Included .env (contains your API keys: keep this backup private)."
fi

BOOKS=$(docker compose exec -T db psql -U bookpilot -d bookpilot -At -c "select count(*) from books" | tr -d '\r')
CHAPTERS=$(docker compose exec -T db psql -U bookpilot -d bookpilot -At -c "select count(*) from chapters" | tr -d '\r')
MIGRATION=$(docker compose exec -T db psql -U bookpilot -d bookpilot -At -c "select version_num from alembic_version" | tr -d '\r')
cat > "$WORK/backup/manifest.txt" <<EOF
BookPilot backup
created:    $(date -u +%Y-%m-%dT%H:%M:%SZ)
host:       $(hostname)
git commit: $(git rev-parse --short HEAD 2>/dev/null || echo unknown)
migration:  $MIGRATION
books:      $BOOKS
chapters:   $CHAPTERS
env file:   $WITH_ENV
EOF

COPYFILE_DISABLE=1 tar --no-xattrs -C "$WORK/backup" -czf "$OUT" .
echo "Backup written to $OUT ($(du -h "$OUT" | cut -f1)): $BOOKS books, $CHAPTERS chapters."
