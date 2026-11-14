#!/usr/bin/env bash
# Write a timestamped archive containing a Postgres custom-format dump and a copy of the env file.
# Auto: the Compose database when it is running, otherwise the systemd host database.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="auto"
BACKUP_DIR="${BACKUP_DIR:-${ROOT}/backups}"

log() { printf '[leadpilot] %s\n' "$*"; }
die() { printf '[leadpilot] ERROR: %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Usage: bash scripts/backup.sh [--source auto|docker|systemd]

Creates backups/leadpilot-YYYYMMDDTHHMMSSZ.tar.gz containing:
  database.dump   pg_dump custom format, no ownership or ACLs
  leadpilot.env   the env file used by that install
  MANIFEST.txt    source, time, and database name (no secret values)

--source auto      Compose db when it is running, otherwise /etc/leadpilot/leadpilot.env
--source docker    the database in docker-compose.yml
--source systemd   the host Postgres described by /etc/leadpilot/leadpilot.env

Set BACKUP_DIR to write the archive somewhere else. The archive is mode 600.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h) usage; exit 0 ;;
    --source)
      [[ $# -ge 2 ]] || die "--source needs auto, docker, or systemd"
      SOURCE="$2"
      shift 2
      ;;
    --source=*) SOURCE="${1#*=}"; shift ;;
    *) die "Unknown argument: $1 (see --help)" ;;
  esac
done

case "$SOURCE" in
  auto|docker|systemd) ;;
  *) die "--source must be auto, docker, or systemd" ;;
esac

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

docker_db_running() {
  command -v docker >/dev/null 2>&1 || return 1
  docker compose ps --status running --services 2>/dev/null | grep -qx 'db'
}

as_postgres() {
  if [[ "$(id -u)" -eq 0 ]]; then
    runuser -u postgres -- "$@"
  else
    sudo -n -u postgres -- "$@"
  fi
}

parse_database_url() {
  local url="$1"
  python3 - "$url" <<'PY'
import shlex
import sys
from urllib.parse import unquote, urlparse

raw = sys.argv[1].strip()
if raw.startswith("postgresql+psycopg://"):
    raw = "postgresql://" + raw[len("postgresql+psycopg://"):]
elif raw.startswith("postgres://"):
    raw = "postgresql://" + raw[len("postgres://"):]
parsed = urlparse(raw)
name = (parsed.path or "/leadpilot").lstrip("/") or "leadpilot"
fields = {
    "PGUSER": unquote(parsed.username or "leadpilot"),
    "PGPASSWORD": unquote(parsed.password or ""),
    "PGHOST": parsed.hostname or "127.0.0.1",
    "PGPORT": str(parsed.port or 5432),
    "PGDATABASE": name,
}
for key, value in fields.items():
    print(f"{key}={shlex.quote(value)}")
PY
}

dump_docker() {
  local user db
  [[ -f "${ROOT}/.env" ]] || die "Missing ${ROOT}/.env"
  user="$(read_env_key "${ROOT}/.env" POSTGRES_USER || true)"
  db="$(read_env_key "${ROOT}/.env" POSTGRES_DB || true)"
  user="${user:-leadpilot}"
  db="${db:-leadpilot}"
  (
    cd "$ROOT"
    docker compose exec -T db pg_dump -U "$user" -d "$db" -Fc --no-owner --no-acl
  ) > "${WORKDIR}/database.dump"
  cp "${ROOT}/.env" "${WORKDIR}/leadpilot.env"
  DB_NAME="$db"
  PG_VERSION="$(cd "$ROOT" && docker compose exec -T db postgres --version | tr -d '\r')"
  SOURCE_USED="docker"
}

dump_systemd() {
  local env_file url
  env_file="/etc/leadpilot/leadpilot.env"
  [[ -r "$env_file" ]] || die "Cannot read ${env_file}. Run with sudo on the systemd server."
  url="$(read_env_key "$env_file" DATABASE_URL || true)"
  [[ -n "$url" ]] || die "${env_file} has no DATABASE_URL"
  command -v python3 >/dev/null 2>&1 || die "python3 is required to read DATABASE_URL"
  # shellcheck disable=SC2046
  eval "$(parse_database_url "$url")"
  if ! as_postgres pg_dump -Fc --no-owner --no-acl -d "$PGDATABASE" > "${WORKDIR}/database.dump"; then
    log "Peer authentication failed; retrying with the DATABASE_URL host and password"
    : > "${WORKDIR}/database.dump"
    PGPASSWORD="$PGPASSWORD" pg_dump \
      -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
      -Fc --no-owner --no-acl > "${WORKDIR}/database.dump"
  fi
  cp "$env_file" "${WORKDIR}/leadpilot.env"
  DB_NAME="$PGDATABASE"
  if as_postgres postgres --version >/dev/null 2>&1; then
    PG_VERSION="$(as_postgres postgres --version | tr -d '\r')"
  else
    PG_VERSION="$(postgres --version 2>/dev/null | tr -d '\r' || echo unknown)"
  fi
  SOURCE_USED="systemd"
  unset PGPASSWORD PGUSER || true
}

WORKDIR="$(mktemp -d)"
chmod 700 "$WORKDIR"
cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT

cd "$ROOT"
case "$SOURCE" in
  docker) dump_docker ;;
  systemd) dump_systemd ;;
  auto)
    if docker_db_running; then
      dump_docker
    else
      dump_systemd
    fi
    ;;
esac

[[ -s "${WORKDIR}/database.dump" ]] || die "pg_dump wrote an empty file"
[[ "$(head -c 5 "${WORKDIR}/database.dump")" == "PGDMP" ]] || die "pg_dump did not write a custom-format archive"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
archive="${BACKUP_DIR}/leadpilot-${stamp}.tar.gz"

cat > "${WORKDIR}/MANIFEST.txt" <<EOF
created_at=${stamp}
source=${SOURCE_USED}
database=${DB_NAME}
postgres=${PG_VERSION}
format=custom
note=Copy SESSION_SECRET and ENCRYPTION_KEY into the new .env unchanged. Compose sets DATABASE_URL for the container.
EOF

chmod 600 "${WORKDIR}/database.dump" "${WORKDIR}/leadpilot.env" "${WORKDIR}/MANIFEST.txt"
tar -C "$WORKDIR" -czf "$archive" database.dump leadpilot.env MANIFEST.txt
chmod 600 "$archive"
log "Wrote ${archive}"
