#!/usr/bin/env bash
set -Eeuo pipefail

# LeadPilot fresh Ubuntu bootstrap
APP_DIR="/opt/leadpilot-ai"
REPO_URL="https://github.com/vibhvesh/LeadPilot-AI.git"
BRANCH="main"
DOMAIN="leads.canberravision.com"
EXPECTED_IPV4="130.250.191.136"

log() { printf '\n[LeadPilot] %s\n' "$*"; }
fail() { echo "[LeadPilot] ERROR: $*" >&2; exit 1; }

[[ "${EUID}" -eq 0 ]] || fail "Run as root: curl -fsSL https://raw.githubusercontent.com/vibhvesh/LeadPilot-AI/main/bootstrap.sh | bash"
[[ -r /etc/os-release ]] || fail "Cannot identify Linux distribution."
. /etc/os-release
[[ "${ID}" == "ubuntu" ]] || fail "This installer supports Ubuntu only."
[[ "${VERSION_ID%%.*}" == "24" ]] || log "Ubuntu ${VERSION_ID} detected. Ubuntu 24.04 LTS is the recommended baseline."

if [[ -e "${APP_DIR}" ]]; then
  fail "${APP_DIR} already exists. This bootstrap is for a fresh server and will not overwrite an existing installation."
fi

export DEBIAN_FRONTEND=noninteractive
log "Installing base packages..."
apt-get update
apt-get install -y ca-certificates curl git openssl

log "Installing Docker Engine and Compose..."
curl -fsSL https://get.docker.com -o /tmp/leadpilot-get-docker.sh
sh /tmp/leadpilot-get-docker.sh
rm -f /tmp/leadpilot-get-docker.sh
systemctl enable --now docker
docker compose version >/dev/null 2>&1 || fail "Docker Compose plugin installation failed."

log "Checking DNS for ${DOMAIN}..."
resolved_ips="$(getent ahostsv4 "${DOMAIN}" | awk '{print $1}' | sort -u || true)"
[[ -n "${resolved_ips}" ]] || fail "${DOMAIN} does not resolve yet. Add an A record pointing to ${EXPECTED_IPV4}, wait for DNS propagation, then rerun."
if ! grep -Fxq "${EXPECTED_IPV4}" <<< "${resolved_ips}"; then
  fail "${DOMAIN} resolves to: ${resolved_ips}; expected ${EXPECTED_IPV4}. Correct the DNS A record before continuing."
fi

log "Cloning LeadPilot from GitHub..."
git clone --depth 1 --branch "${BRANCH}" "${REPO_URL}" "${APP_DIR}"
cd "${APP_DIR}"

[[ -f docker-compose.yml ]] || fail "docker-compose.yml is missing from the repository."
[[ -f .env.example ]] || fail ".env.example is missing from the repository."

log "Creating secure environment configuration..."
db_password="$(openssl rand -hex 32)"
admin_api_key="$(openssl rand -hex 32)"
session_secret="$(openssl rand -hex 48)"
cat > .env <<EOF
DB_PASSWORD=${db_password}
ADMIN_API_KEY=${admin_api_key}
DATABASE_URL=postgresql+psycopg://leadpilot:${db_password}@db:5432/leadpilot
PUBLIC_BASE_URL=https://${DOMAIN}
SESSION_SECRET=${session_secret}
SESSION_COOKIE_NAME=canberraai_session
SESSION_MAX_AGE_SECONDS=28800
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_DISCOVERY_URL=https://accounts.google.com/.well-known/openid-configuration
GOOGLE_REDIRECT_URI=https://${DOMAIN}/auth/google/callback
SUPER_ADMIN_EMAIL=vibhvesh@gmail.com
ALLOWED_GOOGLE_WORKSPACE_DOMAIN=linktms.com
EOF
chmod 600 .env

if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
  log "Opening HTTP and HTTPS in UFW..."
  ufw allow 80/tcp
  ufw allow 443/tcp
  ufw allow 443/udp
fi

log "Validating Docker Compose configuration..."
docker compose config -q

log "Building and starting LeadPilot..."
docker compose up -d --build

log "Waiting for application health..."
app_ok=0
for attempt in $(seq 1 60); do
  if curl -fsS --max-time 3 http://127.0.0.1:1102/health >/dev/null; then
    app_ok=1
    break
  fi
  sleep 2
done
[[ "${app_ok}" -eq 1 ]] || {
  docker compose ps
  docker compose logs --tail=100 app db
  fail "Application health check failed. See logs above."
}

log "Waiting for Caddy to obtain HTTPS certificate..."
https_ok=0
for attempt in $(seq 1 90); do
  if curl -fsSI --max-time 5 "https://${DOMAIN}" >/dev/null 2>&1; then
    https_ok=1
    break
  fi
  sleep 2
done

docker compose ps
if [[ "${https_ok}" -eq 1 ]]; then
  log "SUCCESS: https://${DOMAIN} is responding over HTTPS."
else
  log "Application is running, but HTTPS has not been confirmed."
  echo "Check provider firewall: allow inbound TCP 80 and 443 (and optionally UDP 443)."
  echo "Then inspect: cd ${APP_DIR} && docker compose logs --tail=100 proxy"
  exit 2
fi

log "LeadPilot bootstrap completed."
echo "URL: https://${DOMAIN}"
echo "Install directory: ${APP_DIR}"
echo "Generated secrets are stored in ${APP_DIR}/.env (root-readable only)."
echo "Google Workspace login is not enabled yet; configure OAuth only after its implementation."
