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
if [[ ! -f .env ]]; then
  cp .env.example .env
  PASSWORD="$(openssl rand -hex 24)"
  KEY="$(openssl rand -hex 32)"
  sed -i "s/REPLACE_WITH_STRONG_RANDOM_PASSWORD/$PASSWORD/g" .env
  sed -i "s/REPLACE_WITH_STRONG_RANDOM_ADMIN_KEY/$KEY/g" .env
  chmod 600 .env
  echo "Generated local database password and admin API key in $DEST/.env"
fi
docker compose up -d --build
echo "LeadPilot AI health: http://127.0.0.1:1102/health"
echo "The service binds to localhost for safety until HTTPS and OAuth are configured."
