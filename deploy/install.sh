#!/usr/bin/env bash
# CanberraAI LeadPilot — single-server installer for Ubuntu 22.04+ and Debian 12+.
#
# Interactive:
#   curl -fsSL https://raw.githubusercontent.com/vibhvesh/LeadPilot-AI/main/deploy/install.sh | sudo bash
#
# Non-interactive (the script is on stdin, so flags go after -s --):
#   curl -fsSL https://raw.githubusercontent.com/vibhvesh/LeadPilot-AI/main/deploy/install.sh | sudo bash -s -- \
#     --domain leads.example.com --email admin@example.com \
#     --super-admin vibhvesh@gmail.com --demo-mode false \
#     --google-client-id ID --google-client-secret SECRET
#
# From a checkout: sudo bash deploy/install.sh --domain leads.example.com --email admin@example.com
# Upgrade:        sudo bash deploy/install.sh --upgrade
# Remove service: sudo bash deploy/install.sh --uninstall
# Also drop data: sudo bash deploy/install.sh --uninstall --purge
#
# Re-running install never overwrites keys already in /etc/leadpilot/leadpilot.env.
# It only appends keys that are missing.

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/vibhvesh/LeadPilot-AI.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
LEADPILOT_ROOT="${LEADPILOT_ROOT:-/opt/leadpilot}"
APP_DIR="${APP_DIR:-${LEADPILOT_ROOT}/app}"
ENV_DIR="${ENV_DIR:-/etc/leadpilot}"
ENV_FILE="${ENV_FILE:-${ENV_DIR}/leadpilot.env}"
PYTHON_DIR="${PYTHON_DIR:-${LEADPILOT_ROOT}/python}"
SERVICE_NAME="${SERVICE_NAME:-leadpilot}"
APP_PORT="${APP_PORT:-8000}"
DB_NAME="${DB_NAME:-leadpilot}"
DB_USER="${DB_USER:-leadpilot}"
NGINX_SITE="${NGINX_SITE:-leadpilot}"

MODE="install"
PURGE="false"
DOMAIN=""
EMAIL=""
SUPER_ADMIN=""
GOOGLE_CLIENT_ID=""
GOOGLE_CLIENT_SECRET=""
DEMO_MODE=""
XAI_API_KEY=""
GEMINI_API_KEY=""
OPENAI_API_KEY=""
TAVILY_API_KEY=""
BRAVE_API_KEY=""
SEARCH_API_KEY=""
X_API_KEY=""
GROKBOT_WEBHOOK_URL=""
GROKBOT_WEBHOOK_SECRET=""
HTTPS_READY="false"

log() { printf '\n[leadpilot] %s\n' "$*"; }
warn() { printf '\n[leadpilot] WARNING: %s\n' "$*" >&2; }
die() { printf '\n[leadpilot] ERROR: %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Usage: install.sh [install|flags] | --upgrade | --uninstall [--purge]

Flags (also accepted as --flag=value):
  --domain DOMAIN                 Public hostname. HTTPS is requested when it points here.
  --email EMAIL                   Email for Let's Encrypt.
  --super-admin EMAIL             Super Admin Google account. Default: vibhvesh@gmail.com
  --google-client-id ID
  --google-client-secret SECRET
  --demo-mode true|false          Allow demo sign-in without Google. Default: false
  --xai-api-key KEY
  --gemini-api-key KEY
  --openai-api-key KEY
  --tavily-api-key KEY
  --brave-api-key KEY
  --search-api-key KEY
  --x-api-key KEY                 X bearer token. Public read only. Never posts.
  --grokbot-webhook-url URL
  --grokbot-webhook-secret SECRET
  --upgrade                       git pull, install deps, apply schema, restart
  --uninstall                     Remove the systemd unit and nginx site
  --purge                         With --uninstall, also drop the database, env file, and /opt/leadpilot
EOF
}

require_root() {
  local euid
  euid="$(id -u)"
  [[ "$euid" -eq 0 ]] || die "Run as root: sudo bash deploy/install.sh"
}

as_user() {
  local user="$1"
  shift
  runuser -u "$user" -- "$@"
}

systemd_available() {
  [[ -d /run/systemd/system ]] && command -v systemctl >/dev/null 2>&1
}

check_os() {
  [[ -r /etc/os-release ]] || die "Cannot identify this operating system."
  # shellcheck disable=SC1091
  . /etc/os-release
  local major="${VERSION_ID%%.*}"
  case "${ID:-}" in
    ubuntu)
      [[ "$major" -ge 22 ]] || die "Ubuntu 22.04 or newer is required (found ${VERSION_ID:-unknown})."
      ;;
    debian)
      [[ "$major" -ge 12 ]] || die "Debian 12 or newer is required (found ${VERSION_ID:-unknown})."
      ;;
    *)
      die "This installer supports Ubuntu 22.04+ and Debian 12+ (found ${ID:-unknown})."
      ;;
  esac
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h) usage; exit 0 ;;
      --upgrade) MODE="upgrade"; shift ;;
      --uninstall) MODE="uninstall"; shift ;;
      --purge) PURGE="true"; shift ;;
      --domain) DOMAIN="${2:-}"; shift 2 ;;
      --domain=*) DOMAIN="${1#*=}"; shift ;;
      --email) EMAIL="${2:-}"; shift 2 ;;
      --email=*) EMAIL="${1#*=}"; shift ;;
      --super-admin) SUPER_ADMIN="${2:-}"; shift 2 ;;
      --super-admin=*) SUPER_ADMIN="${1#*=}"; shift ;;
      --google-client-id) GOOGLE_CLIENT_ID="${2:-}"; shift 2 ;;
      --google-client-id=*) GOOGLE_CLIENT_ID="${1#*=}"; shift ;;
      --google-client-secret) GOOGLE_CLIENT_SECRET="${2:-}"; shift 2 ;;
      --google-client-secret=*) GOOGLE_CLIENT_SECRET="${1#*=}"; shift ;;
      --demo-mode) DEMO_MODE="$(normalize_bool "${2:-}")"; shift 2 ;;
      --demo-mode=*) DEMO_MODE="$(normalize_bool "${1#*=}")"; shift ;;
      --xai-api-key) XAI_API_KEY="${2:-}"; shift 2 ;;
      --xai-api-key=*) XAI_API_KEY="${1#*=}"; shift ;;
      --gemini-api-key) GEMINI_API_KEY="${2:-}"; shift 2 ;;
      --gemini-api-key=*) GEMINI_API_KEY="${1#*=}"; shift ;;
      --openai-api-key) OPENAI_API_KEY="${2:-}"; shift 2 ;;
      --openai-api-key=*) OPENAI_API_KEY="${1#*=}"; shift ;;
      --tavily-api-key) TAVILY_API_KEY="${2:-}"; shift 2 ;;
      --tavily-api-key=*) TAVILY_API_KEY="${1#*=}"; shift ;;
      --brave-api-key) BRAVE_API_KEY="${2:-}"; shift 2 ;;
      --brave-api-key=*) BRAVE_API_KEY="${1#*=}"; shift ;;
      --search-api-key) SEARCH_API_KEY="${2:-}"; shift 2 ;;
      --search-api-key=*) SEARCH_API_KEY="${1#*=}"; shift ;;
      --x-api-key) X_API_KEY="${2:-}"; shift 2 ;;
      --x-api-key=*) X_API_KEY="${1#*=}"; shift ;;
      --grokbot-webhook-url) GROKBOT_WEBHOOK_URL="${2:-}"; shift 2 ;;
      --grokbot-webhook-url=*) GROKBOT_WEBHOOK_URL="${1#*=}"; shift ;;
      --grokbot-webhook-secret) GROKBOT_WEBHOOK_SECRET="${2:-}"; shift 2 ;;
      --grokbot-webhook-secret=*) GROKBOT_WEBHOOK_SECRET="${1#*=}"; shift ;;
      *) die "Unknown argument: $1 (see --help)" ;;
    esac
  done
}

normalize_bool() {
  local value="${1,,}"
  case "$value" in
    1|true|yes|y) printf 'true' ;;
    0|false|no|n) printf 'false' ;;
    *) die "Expected true or false, got: ${1}" ;;
  esac
}

prompt_if_empty() {
  local var_name="$1"
  local label="$2"
  local default="${3:-}"
  local current="${!var_name}"
  [[ -z "$current" ]] || return 0
  [[ -r /dev/tty ]] || { printf -v "$var_name" '%s' "$default"; return 0; }
  local reply
  if [[ -n "$default" ]]; then
    read -r -p "${label} [${default}]: " reply </dev/tty || true
  else
    read -r -p "${label}: " reply </dev/tty || true
  fi
  printf -v "$var_name" '%s' "${reply:-$default}"
}

collect_settings() {
  # Only ask on a first install. A later run must not change stored keys.
  [[ ! -f "$ENV_FILE" ]] || return 0
  [[ "$MODE" == "install" ]] || return 0
  prompt_if_empty DOMAIN "Domain name (leave empty to stay on HTTP)" ""
  if [[ -n "$DOMAIN" ]]; then
    prompt_if_empty EMAIL "Let's Encrypt email" ""
  fi
  prompt_if_empty SUPER_ADMIN "Super Admin email" "vibhvesh@gmail.com"
  prompt_if_empty DEMO_MODE "Enable demo sign-in without Google (true/false)" "false"
  DEMO_MODE="$(normalize_bool "$DEMO_MODE")"
  prompt_if_empty GOOGLE_CLIENT_ID "Google OAuth client id (optional)" ""
  prompt_if_empty GOOGLE_CLIENT_SECRET "Google OAuth client secret (optional)" ""
}

quote_env() {
  local value="$1"
  value="${value//\'/\'\\\'\'}"
  printf "'%s'" "$value"
}

env_has_key() {
  local key="$1"
  [[ -f "$ENV_FILE" ]] || return 1
  grep -qE "^${key}=" "$ENV_FILE"
}

append_env_if_missing() {
  local key="$1"
  local value="$2"
  if env_has_key "$key"; then
    return 0
  fi
  printf '%s=%s\n' "$key" "$(quote_env "$value")" >>"$ENV_FILE"
  log "Added ${key}"
}

install_packages() {
  log "Installing packages"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y \
    ca-certificates curl git openssl \
    nginx \
    postgresql postgresql-contrib \
    certbot python3-certbot-nginx
}

ensure_user() {
  if ! id leadpilot >/dev/null 2>&1; then
    log "Creating system user leadpilot"
    useradd --system --create-home --home-dir "$LEADPILOT_ROOT" --shell /usr/sbin/nologin leadpilot
  fi
  install -d -o leadpilot -g leadpilot -m 0755 "$LEADPILOT_ROOT" "$PYTHON_DIR"
}

install_uv() {
  if ! command -v uv >/dev/null 2>&1; then
    log "Installing uv"
    curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
  fi
  command -v uv >/dev/null 2>&1 || die "uv was not installed into /usr/local/bin"
}

sync_repo() {
  if [[ -d "${APP_DIR}/.git" ]]; then
    log "Updating ${APP_DIR}"
    git config --system --get-all safe.directory 2>/dev/null | grep -qx "$APP_DIR" \
      || git config --system --add safe.directory "$APP_DIR"
    as_user leadpilot git -C "$APP_DIR" fetch --depth 1 origin "$REPO_BRANCH"
    as_user leadpilot git -C "$APP_DIR" checkout "$REPO_BRANCH"
    as_user leadpilot git -C "$APP_DIR" pull --ff-only origin "$REPO_BRANCH"
  else
    [[ ! -e "$APP_DIR" ]] || die "${APP_DIR} exists but is not a git checkout."
    log "Cloning LeadPilot into ${APP_DIR}"
    as_user leadpilot git clone --depth 1 --branch "$REPO_BRANCH" "$REPO_URL" "$APP_DIR"
  fi
}

install_python_deps() {
  log "Installing Python 3.12 and application dependencies"
  as_user leadpilot env UV_PYTHON_INSTALL_DIR="$PYTHON_DIR" uv python install 3.12
  if [[ ! -x "${APP_DIR}/.venv/bin/python" ]]; then
    as_user leadpilot env UV_PYTHON_INSTALL_DIR="$PYTHON_DIR" \
      uv venv --python 3.12 "${APP_DIR}/.venv"
  fi
  as_user leadpilot env UV_PYTHON_INSTALL_DIR="$PYTHON_DIR" \
    uv pip install --python "${APP_DIR}/.venv/bin/python" -r "${APP_DIR}/requirements.txt"
}

role_exists() {
  local found
  found="$(as_user postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" || true)"
  [[ "$found" == "1" ]]
}

database_exists() {
  local found
  found="$(as_user postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" || true)"
  [[ "$found" == "1" ]]
}

ensure_postgres_running() {
  if systemd_available; then
    systemctl enable postgresql >/dev/null 2>&1 || true
    if systemctl start postgresql; then
      return 0
    fi
  fi
  if command -v pg_ctlcluster >/dev/null 2>&1; then
    local version
    version="$(find /etc/postgresql -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | head -n 1 || true)"
    if [[ -n "$version" ]] && pg_ctlcluster "$version" main start; then
      return 0
    fi
  fi
  if command -v service >/dev/null 2>&1 && service postgresql start; then
    return 0
  fi
  die "PostgreSQL did not start."
}

ensure_database() {
  local password url
  ensure_postgres_running
  if env_has_key DATABASE_URL; then
    log "Database URL already recorded; leaving the Postgres role password unchanged"
    if ! database_exists; then
      as_user postgres createdb --owner="$DB_USER" "$DB_NAME"
    fi
    return 0
  fi
  install -d -m 0755 "$ENV_DIR"
  if [[ ! -f "$ENV_FILE" ]]; then
    (umask 077 && touch "$ENV_FILE")
    chmod 600 "$ENV_FILE"
  fi
  if role_exists; then
    die "Postgres role ${DB_USER} already exists but ${ENV_FILE} has no DATABASE_URL. Add that key, then re-run."
  fi
  password="$(openssl rand -hex 24)"
  log "Creating Postgres role and database ${DB_NAME}"
  as_user postgres psql -v ON_ERROR_STOP=1 -c "CREATE ROLE ${DB_USER} LOGIN PASSWORD '${password}'"
  if ! database_exists; then
    as_user postgres createdb --owner="$DB_USER" "$DB_NAME"
  fi
  url="postgresql+psycopg://${DB_USER}:${password}@127.0.0.1:5432/${DB_NAME}"
  append_env_if_missing DATABASE_URL "$url"
}

should_disable_ipv6() {
  local routes
  routes="$(ip -6 route show default 2>/dev/null || true)"
  [[ -z "${routes//[[:space:]]/}" ]]
}

disable_broken_ipv6() {
  if ! should_disable_ipv6; then
    log "IPv6 default route is present; leaving IPv6 enabled"
    return 0
  fi
  log "No global IPv6 route; disabling IPv6 so outbound HTTPS does not time out"
  cat >/etc/sysctl.d/99-leadpilot-ipv6.conf <<'EOF'
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
EOF
  sysctl --system >/dev/null || warn "sysctl reported errors while disabling IPv6. Check /etc/sysctl.d/99-leadpilot-ipv6.conf"
}

public_ipv4() {
  curl -4 -fsS --max-time 5 https://api.ipify.org 2>/dev/null || true
}

domain_points_here() {
  local domain="$1"
  [[ -n "$domain" ]] || return 1
  local local_ips public_ip ip
  local -a resolved_ips=()
  mapfile -t resolved_ips < <(getent ahostsv4 "$domain" 2>/dev/null | awk '{print $1}' | sort -u || true)
  [[ "${#resolved_ips[@]}" -gt 0 ]] || return 1
  local_ips="$(hostname -I 2>/dev/null || true)"
  public_ip="$(public_ipv4)"
  for ip in "${resolved_ips[@]}"; do
    [[ -n "$ip" ]] || continue
    if [[ " ${local_ips} " == *" ${ip} "* ]] || [[ -n "$public_ip" && "$ip" == "$public_ip" ]]; then
      return 0
    fi
    if ip -4 addr show | grep -q "inet ${ip}/"; then
      return 0
    fi
  done
  return 1
}

write_env() {
  local base_url secure
  install -d -m 0755 "$ENV_DIR"
  if [[ ! -f "$ENV_FILE" ]]; then
    (umask 077 && touch "$ENV_FILE")
  fi
  chmod 600 "$ENV_FILE"
  chown root:root "$ENV_FILE"

  if [[ "$HTTPS_READY" == "true" ]]; then
    base_url="https://${DOMAIN}"
    secure="true"
  elif [[ -n "$DOMAIN" ]]; then
    base_url="http://${DOMAIN}"
    secure="false"
  else
    base_url="http://127.0.0.1:${APP_PORT}"
    secure="false"
  fi

  [[ -n "$SUPER_ADMIN" ]] || SUPER_ADMIN="vibhvesh@gmail.com"
  [[ -n "$DEMO_MODE" ]] || DEMO_MODE="false"

  append_env_if_missing APP_ENV "production"
  append_env_if_missing DEMO_MODE "$DEMO_MODE"
  append_env_if_missing PUBLIC_BASE_URL "$base_url"
  append_env_if_missing SUPER_ADMIN_EMAIL "$SUPER_ADMIN"
  append_env_if_missing SESSION_SECRET "$(openssl rand -hex 32)"
  append_env_if_missing SESSION_COOKIE_NAME "leadpilot_session"
  append_env_if_missing SESSION_MAX_AGE_SECONDS "28800"
  append_env_if_missing SESSION_COOKIE_SECURE "$secure"
  append_env_if_missing ENCRYPTION_KEY "$(openssl rand -hex 32)"
  append_env_if_missing GOOGLE_CLIENT_ID "$GOOGLE_CLIENT_ID"
  append_env_if_missing GOOGLE_CLIENT_SECRET "$GOOGLE_CLIENT_SECRET"
  append_env_if_missing GOOGLE_DISCOVERY_URL "https://accounts.google.com/.well-known/openid-configuration"
  append_env_if_missing GOOGLE_REDIRECT_URI "${base_url}/auth/google/callback"
  append_env_if_missing SEARCH_PROVIDER "auto"
  append_env_if_missing SEARCH_API_KEY "$SEARCH_API_KEY"
  append_env_if_missing TAVILY_API_KEY "$TAVILY_API_KEY"
  append_env_if_missing BRAVE_API_KEY "$BRAVE_API_KEY"
  append_env_if_missing X_API_KEY "$X_API_KEY"
  append_env_if_missing XAI_API_KEY "$XAI_API_KEY"
  append_env_if_missing GEMINI_API_KEY "$GEMINI_API_KEY"
  append_env_if_missing OPENAI_API_KEY "$OPENAI_API_KEY"
  append_env_if_missing XAI_MODEL "grok-3"
  append_env_if_missing GEMINI_MODEL "gemini-2.0-flash"
  append_env_if_missing OPENAI_MODEL "gpt-4o-mini"
  append_env_if_missing AI_SEARCH_MAX_ROUNDS "2"
  append_env_if_missing GROKBOT_WEBHOOK_URL "$GROKBOT_WEBHOOK_URL"
  append_env_if_missing GROKBOT_WEBHOOK_SECRET "$GROKBOT_WEBHOOK_SECRET"
}

apply_schema() {
  log "Applying database schema"
  local runner
  runner="$(mktemp)"
  cat >"$runner" <<'PY'
import os
import sys

app_dir = os.environ["LEADPILOT_APP_DIR"]
os.chdir(app_dir)
sys.path.insert(0, app_dir)

from app.core.config import get_settings
from app.core.database import init_database, session_scope
from app.core.seed import seed

settings = get_settings()
init_database(settings.resolved_database_url())
with session_scope() as db:
    seed(db, settings)
print("schema ok")
PY
  (
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
    cd "$APP_DIR"
    LEADPILOT_APP_DIR="$APP_DIR" "${APP_DIR}/.venv/bin/python" "$runner"
  )
  rm -f "$runner"
}

write_systemd_unit() {
  cat >"/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=CanberraAI LeadPilot
After=network-online.target postgresql.service
Wants=network-online.target
Requires=postgresql.service

[Service]
Type=simple
User=leadpilot
Group=leadpilot
WorkingDirectory=${APP_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${APP_DIR}/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port ${APP_PORT} --workers 1
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
  if systemd_available; then
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
  else
    warn "systemd is not running. The unit file is installed and will start after a reboot into systemd."
  fi
}

nginx_site_path() {
  if [[ -d /etc/nginx/sites-available ]]; then
    printf '/etc/nginx/sites-available/%s' "$NGINX_SITE"
  else
    printf '/etc/nginx/conf.d/%s.conf' "$NGINX_SITE"
  fi
}

write_nginx_site() {
  local server_name path
  server_name="${DOMAIN:-_}"
  path="$(nginx_site_path)"
  cat >"$path" <<EOF
server {
    listen 80;
    server_name ${server_name};
    client_max_body_size 16m;

    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
EOF
  if [[ -d /etc/nginx/sites-enabled ]]; then
    ln -sfn "$path" "/etc/nginx/sites-enabled/${NGINX_SITE}"
    if [[ -e /etc/nginx/sites-enabled/default ]]; then
      rm -f /etc/nginx/sites-enabled/default
      log "Disabled the default nginx site so LeadPilot can answer on port 80"
    fi
  fi
  nginx -t
  if systemd_available; then
    systemctl enable nginx
    systemctl reload nginx || systemctl restart nginx
  elif ! pgrep -x nginx >/dev/null 2>&1; then
    nginx
  fi
}

maybe_https() {
  HTTPS_READY="false"
  [[ -n "$DOMAIN" ]] || return 0
  if ! domain_points_here "$DOMAIN"; then
    warn "${DOMAIN} does not resolve to this server yet. Leaving the site on HTTP."
    return 0
  fi
  if [[ -z "$EMAIL" ]]; then
    warn "No --email was given, so Certbot was skipped. The site stays on HTTP."
    return 0
  fi
  log "Requesting a certificate for ${DOMAIN}"
  if certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect; then
    HTTPS_READY="true"
  else
    warn "Certbot did not issue a certificate. The site stays on HTTP."
  fi
}

restart_service() {
  if systemd_available; then
    systemctl restart "$SERVICE_NAME"
    return 0
  fi
  warn "systemd is not running; starting one uvicorn worker directly"
  if [[ -f /run/leadpilot.pid ]] && kill -0 "$(cat /run/leadpilot.pid)" 2>/dev/null; then
    kill "$(cat /run/leadpilot.pid)" || true
    sleep 1
  fi
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
  as_user leadpilot bash -c "cd '$APP_DIR' && exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port ${APP_PORT} --workers 1" \
    >/var/log/leadpilot.log 2>&1 &
  echo "$!" >/run/leadpilot.pid
}

health_check() {
  log "Checking http://127.0.0.1:${APP_PORT}/health"
  for _attempt in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do
    if curl -fsS --max-time 3 "http://127.0.0.1:${APP_PORT}/health" >/dev/null; then
      log "Health check passed on attempt ${_attempt}"
      return 0
    fi
    sleep 1
  done
  if command -v journalctl >/dev/null 2>&1; then
    journalctl -u "$SERVICE_NAME" -n 80 --no-pager || true
  fi
  if [[ -f /var/log/leadpilot.log ]]; then
    tail -n 80 /var/log/leadpilot.log || true
  fi
  die "LeadPilot did not become healthy. See: journalctl -u ${SERVICE_NAME}"
}

print_summary() {
  local url
  if [[ "$HTTPS_READY" == "true" ]]; then
    url="https://${DOMAIN}"
  elif [[ -n "$DOMAIN" ]]; then
    url="http://${DOMAIN}"
  else
    url="http://127.0.0.1:${APP_PORT}"
  fi
  log "LeadPilot is running at ${url}"
  log "Environment file: ${ENV_FILE} (existing keys are left unchanged)"
  if [[ "${DEMO_MODE:-false}" == "true" ]]; then
    warn "Demo sign-in is enabled. Set DEMO_MODE=false in ${ENV_FILE} before exposing this server."
  fi
}

install_all() {
  require_root
  check_os
  collect_settings
  install_packages
  ensure_user
  disable_broken_ipv6
  install_uv
  sync_repo
  install_python_deps
  ensure_database
  write_nginx_site
  maybe_https
  write_env
  apply_schema
  write_systemd_unit
  restart_service
  health_check
  print_summary
}

upgrade_all() {
  require_root
  check_os
  [[ -d "${APP_DIR}/.git" ]] || die "No checkout at ${APP_DIR}. Run the installer first."
  [[ -f "$ENV_FILE" ]] || die "Missing ${ENV_FILE}. Run the installer first."
  install_uv
  sync_repo
  install_python_deps
  write_env
  apply_schema
  restart_service
  health_check
  log "Upgrade finished"
}

uninstall_all() {
  require_root
  if systemd_available && systemctl list-unit-files "${SERVICE_NAME}.service" >/dev/null 2>&1; then
    systemctl disable --now "$SERVICE_NAME" || true
  fi
  if [[ -f /run/leadpilot.pid ]]; then
    kill "$(cat /run/leadpilot.pid)" >/dev/null 2>&1 || true
    rm -f /run/leadpilot.pid
  fi
  rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
  if systemd_available; then
    systemctl daemon-reload || true
  fi
  if [[ -d /etc/nginx/sites-enabled ]]; then
    rm -f "/etc/nginx/sites-enabled/${NGINX_SITE}"
    rm -f "/etc/nginx/sites-available/${NGINX_SITE}"
  fi
  rm -f "/etc/nginx/conf.d/${NGINX_SITE}.conf"
  if command -v nginx >/dev/null 2>&1 && nginx -t; then
    if systemd_available; then
      systemctl reload nginx || true
    else
      nginx -s reload >/dev/null 2>&1 || true
    fi
  fi
  if [[ "$PURGE" == "true" ]]; then
    if command -v psql >/dev/null 2>&1 && id postgres >/dev/null 2>&1; then
      as_user postgres dropdb --if-exists "$DB_NAME" || true
      as_user postgres psql -c "DROP ROLE IF EXISTS ${DB_USER}" || true
    fi
    rm -rf "$LEADPILOT_ROOT" "$ENV_DIR"
    rm -f /etc/sysctl.d/99-leadpilot-ipv6.conf
    if id leadpilot >/dev/null 2>&1; then
      userdel leadpilot || true
    fi
    log "Purged LeadPilot data, the database, and ${ENV_DIR}"
  else
    log "Removed the service and nginx site. Data remains in ${LEADPILOT_ROOT}, ${ENV_FILE}, and Postgres."
    log "To delete those as well, re-run with --uninstall --purge"
  fi
}

main() {
  parse_args "$@"
  if [[ "$PURGE" == "true" && "$MODE" != "uninstall" ]]; then
    die "--purge is only valid together with --uninstall"
  fi
  case "$MODE" in
    install) install_all ;;
    upgrade) upgrade_all ;;
    uninstall) uninstall_all ;;
    *) die "Unknown mode: ${MODE}" ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
