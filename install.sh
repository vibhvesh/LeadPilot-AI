#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/leadpilot-ai}"
DOMAIN="${DOMAIN:-leads.canberravision.com}"
EXPECTED_IPV4="${EXPECTED_IPV4:-130.250.191.136}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash install.sh"
  exit 1
fi

command -v git >/dev/null || { echo "ERROR: git is not installed."; exit 1; }
command -v docker >/dev/null || { echo "ERROR: Docker is not installed."; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "ERROR: Docker Compose plugin is required."; exit 1; }

if [[ ! -d "${APP_DIR}/.git" ]]; then
  echo "ERROR: Repository not found at ${APP_DIR}."
  echo "Clone it first: git clone https://github.com/vibhvesh/LeadPilot-AI.git ${APP_DIR}"
  exit 1
fi

cd "${APP_DIR}"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: Working tree has local changes. Commit or stash them before installing."
  git status --short
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "ERROR: ${APP_DIR}/.env is missing. Create it from .env.example and set secure values first."
  exit 1
fi

echo "Checking DNS for ${DOMAIN}..."
if ! getent ahostsv4 "${DOMAIN}" | awk '{print $1}' | grep -Fxq "${EXPECTED_IPV4}"; then
  echo "ERROR: ${DOMAIN} does not currently resolve to ${EXPECTED_IPV4}."
  echo "Correct the DNS A record, wait for propagation, then rerun."
  exit 1
fi

echo "Checking application health..."
healthy=0
for attempt in {1..30}; do
  if curl -fsS --max-time 3 http://127.0.0.1:1102/health >/dev/null; then
    healthy=1
    break
  fi
  sleep 2
done
if [[ "${healthy}" -ne 1 ]]; then
  echo "ERROR: App health check failed on 127.0.0.1:1102/health."
  echo "Check: docker compose logs --tail=100 app"
  exit 1
fi

git pull --ff-only origin main
if ! grep -q '^TLS_MODE=' .env; then
  export TLS_MODE=https
fi
if ! grep -q '^LEADPILOT_DOMAIN=' .env; then
  export LEADPILOT_DOMAIN="${DOMAIN}"
fi
if ! grep -q '^LEADPILOT_BIND=' .env; then
  export LEADPILOT_BIND=0.0.0.0
fi
docker compose config -q
docker compose up -d --build --remove-orphans

echo "Waiting for HTTPS certificate and endpoint..."
https_ok=0
for attempt in {1..45}; do
  if curl -fsSI --max-time 5 "https://${DOMAIN}" >/dev/null; then
    https_ok=1
    break
  fi
  sleep 2
done

docker compose ps
if [[ "${https_ok}" -eq 1 ]]; then
  echo "SUCCESS: https://${DOMAIN} is responding over HTTPS."
else
  echo "Deployment completed, but HTTPS is not confirmed yet."
  echo "Check that inbound TCP ports 80 and 443 are allowed and inspect:"
  echo "  docker compose logs --tail=100 proxy"
  echo "  docker compose ps"
  exit 2
fi
