#!/usr/bin/env bash
set -euo pipefail
if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with sudo"; exit 1
fi
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo "Install Docker Engine and Docker Compose plugin first: https://docs.docker.com/engine/install/ubuntu/"
  exit 1
fi
if ! command -v git >/dev/null 2>&1; then
  apt-get update && apt-get install -y git
fi
DEST=/opt/leadpilot-ai
if [[ -e "$DEST/.git" ]]; then
  git -C "$DEST" pull --ff-only
else
  git clone https://github.com/vibhvesh/LeadPilot-AI.git "$DEST"
fi
cd "$DEST"
set_kv() {
  local key="$1" value="$2"
  if grep -q "^${key}=" .env; then
    sed -i "s|^${key}=.*|${key}=${value}|" .env
  else
    printf '%s=%s\n' "$key" "$value" >> .env
  fi
}
if [[ ! -f .env ]]; then
  cp .env.example .env
  set_kv DB_PASSWORD "$(openssl rand -hex 24)"
  set_kv SESSION_SECRET "$(openssl rand -hex 32)"
  set_kv ENCRYPTION_KEY "$(openssl rand -hex 32)"
  set_kv ADMIN_API_KEY "$(openssl rand -hex 32)"
  set_kv APP_ENV production
  set_kv DEMO_MODE false
  set_kv SESSION_COOKIE_SECURE false
  set_kv TLS_MODE http
  set_kv LEADPILOT_BIND 0.0.0.0
  set_kv PUBLIC_BASE_URL "http://127.0.0.1:1102"
  chmod 600 .env
  echo "Generated database password, session secret, and encryption key in $DEST/.env"
fi
docker compose up -d --build
echo "LeadPilot AI health: http://127.0.0.1:1102/health"
echo "HTTP proxy: port 80. Set TLS_MODE=https and LEADPILOT_DOMAIN before pointing DNS here. See DOCKER.md."
