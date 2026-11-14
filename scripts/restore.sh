#!/usr/bin/env bash
# Load a pg_dump from the systemd server, or a backup.sh archive, into the Compose database.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FORCE=0
START=1
DUMP_PATH=""

log() { printf '[leadpilot] %s\n' "$*"; }
die() { printf '[leadpilot] ERROR: %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Usage: bash scripts/restore.sh [--force] [--no-start] <dump-or-archive>

Accepts:
  leadpilot-YYYYMMDDTHHMMSSZ.tar.gz   archive from scripts/backup.sh
  database.dump                        pg_dump custom format (PGDMP)
  backup.sql                           plain pg_dump SQL
  backup.sql.gz                        gzipped plain SQL

The Compose database is left untouched when it already has tables, unless
--force is set. --force drops schema public in the container database and
loads the dump. It does not delete the leadpilot_db volume.

--no-start   leave the app stopped after the load

Run this from a checkout that already has .env (DB_PASSWORD at minimum).
Copy SESSION_SECRET and ENCRYPTION_KEY from the old environment yourself;
this script restores rows, not the container's env file.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h) usage; exit 0 ;;
    --force) FORCE=1; shift ;;
    --no-start) START=0; shift ;;
    --) shift; DUMP_PATH="${1:-}"; shift || true; break ;;
    -*) die "Unknown option: $1 (see --help)" ;;
    *)
      [[ -z "$DUMP_PATH" ]] || die "Unexpected extra argument: $1"
      DUMP_PATH="$1"
      shift
      ;;
  esac
done

[[ -n "$DUMP_PATH" ]] || die "Pass a dump or backup archive. See --help."
[[ -f "$DUMP_PATH" ]] || die "File not found: ${DUMP_PATH}"
[[ -f "${ROOT}/.env" ]] || die "Missing ${ROOT}/.env. Copy .env.example and set DB_PASSWORD."

read_env_key() {
  local file="$1" key="$2" line value
  line="$(grep -E "^${key}=" "$file" | tail -n 1 || true)"
  [[ -n "$line" ]] || return 1
  value="${line#*=}"
  if [[ "$value" == \'*\' ]]; then
    value="${value:1:${#value}-2}"
    value="${value//\'\\\'\'/\'}"
  elif [[ "$value" == \"*\" ]]; then
    value="${value:1:${#value}-2}"
  fi
  printf '%s' "$value"
}

WORKDIR="$(mktemp -d)"
chmod 700 "$WORKDIR"
cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT

inspect_archive() {
  local name
  while IFS= read -r name; do
    case "$name" in
      ""|./) ;;
      /*|../*|*/../*|*/..) die "Archive contains an unsafe path: ${name}" ;;
    esac
  done < <(tar -tzf "$1")
}

resolve_dump() {
  local path="$1" magic name extracted
  magic="$(head -c 5 "$path" | tr -d '\000' || true)"
  case "$path" in
    *.tar.gz|*.tgz)
      inspect_archive "$path"
      tar -xzf "$path" -C "$WORKDIR"
      if [[ -f "${WORKDIR}/database.dump" ]]; then
        printf '%s\n' "${WORKDIR}/database.dump"
        return 0
      fi
      extracted=""
      while IFS= read -r candidate; do
        extracted="$candidate"
        break
      done < <(find "$WORKDIR" -type f \( -name '*.dump' -o -name '*.sql' -o -name '*.sql.gz' -o -name '*.backup' \))
      [[ -n "$extracted" ]] || die "Archive has no database.dump or SQL file"
      printf '%s\n' "$extracted"
      ;;
    *.sql.gz)
      gzip -dc "$path" > "${WORKDIR}/restore.sql"
      printf '%s\n' "${WORKDIR}/restore.sql"
      ;;
    *)
      if [[ "$magic" == "PGDMP" || "$path" == *.dump || "$path" == *.backup || "$path" == *.custom ]]; then
        printf '%s\n' "$path"
      elif [[ "$path" == *.sql ]]; then
        printf '%s\n' "$path"
      else
        die "Unrecognized dump. Use a .dump, .sql, .sql.gz, or backup .tar.gz file."
      fi
      ;;
  esac
}

SQL_FILE="$(resolve_dump "$DUMP_PATH")"
[[ -f "$SQL_FILE" ]] || die "Could not prepare the dump"
magic="$(head -c 5 "$SQL_FILE" | tr -d '\000' || true)"
if [[ "$magic" == "PGDMP" ]]; then
  FORMAT="custom"
else
  FORMAT="sql"
fi

cd "$ROOT"
PG_USER="$(read_env_key .env POSTGRES_USER || true)"
PG_DB="$(read_env_key .env POSTGRES_DB || true)"
PG_USER="${PG_USER:-leadpilot}"
PG_DB="${PG_DB:-leadpilot}"
APP_PORT="$(read_env_key .env LEADPILOT_APP_PORT || true)"
APP_PORT="${APP_PORT:-1102}"
[[ "$PG_USER" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || die "POSTGRES_USER must be a plain identifier"
[[ "$PG_DB" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || die "POSTGRES_DB must be a plain identifier"
[[ "$APP_PORT" =~ ^[0-9]+$ ]] || die "LEADPILOT_APP_PORT must be a number"

log "Starting Postgres"
docker compose up -d db
ready=0
for _attempt in $(seq 1 45); do
  if docker compose exec -T db pg_isready -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
[[ "$ready" -eq 1 ]] || die "Postgres did not become ready. Check: docker compose logs db"

docker compose stop app >/dev/null 2>&1 || true

table_count="$(docker compose exec -T db psql -U "$PG_USER" -d "$PG_DB" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")"
table_count="${table_count//[[:space:]]/}"
if [[ "${table_count}" != "0" && "$FORCE" -ne 1 ]]; then
  die "Database ${PG_DB} already has ${table_count} tables. Re-run with --force to replace the rows in the Compose volume."
fi

if [[ "$FORCE" -eq 1 && "${table_count}" != "0" ]]; then
  log "Replacing ${table_count} tables in ${PG_DB}. The named volume is kept."
fi
docker compose exec -T db psql -U "$PG_USER" -d "$PG_DB" -v ON_ERROR_STOP=1 <<SQL
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO ${PG_USER};
GRANT ALL ON SCHEMA public TO public;
SQL

log "Loading ${FORMAT} dump into ${PG_DB}"
if [[ "$FORMAT" == "custom" ]]; then
  cid="$(docker compose ps -q db)"
  [[ -n "$cid" ]] || die "Postgres container id is missing"
  docker cp "$SQL_FILE" "${cid}:/tmp/leadpilot-restore.dump"
  docker compose exec -T db chmod 644 /tmp/leadpilot-restore.dump
  docker compose exec -T db pg_restore --no-owner --no-acl --exit-on-error -U "$PG_USER" -d "$PG_DB" /tmp/leadpilot-restore.dump
  docker compose exec -T db rm -f /tmp/leadpilot-restore.dump
else
  docker compose exec -T db psql -U "$PG_USER" -d "$PG_DB" -v ON_ERROR_STOP=1 < "$SQL_FILE"
fi

restored="$(docker compose exec -T db psql -U "$PG_USER" -d "$PG_DB" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")"
restored="${restored//[[:space:]]/}"
log "Restore finished. Public tables: ${restored}"

if [[ -f "${WORKDIR}/leadpilot.env" || -f "${WORKDIR}/MANIFEST.txt" ]]; then
  log "The archive also contains the old environment file. Copy SESSION_SECRET and ENCRYPTION_KEY into ${ROOT}/.env unchanged."
  if [[ -f "${WORKDIR}/leadpilot.env" ]]; then
    log "Keys in the archived env file:"
    grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "${WORKDIR}/leadpilot.env" | cut -d= -f1 | sort
  fi
fi

if [[ "$START" -eq 0 ]]; then
  log "App was left stopped (--no-start). Start it with: docker compose up -d"
  exit 0
fi

log "Starting the stack"
docker compose up -d
healthy=0
for _attempt in $(seq 1 30); do
  if curl -fsS --max-time 3 "http://127.0.0.1:${APP_PORT}/health" >/dev/null 2>&1; then
    healthy=1
    break
  fi
  sleep 2
done
if [[ "$healthy" -ne 1 ]]; then
  die "Database was restored, but /health did not succeed. Check: docker compose logs app"
fi
log "Health check passed at http://127.0.0.1:${APP_PORT}/health"
