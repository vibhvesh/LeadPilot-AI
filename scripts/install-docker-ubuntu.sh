#!/usr/bin/env bash
# Install Docker Engine, the Compose plugin, and a UFW policy on Ubuntu 22.04+.
# Does not clone LeadPilot or start the stack. See DOCKER.md for that.
set -euo pipefail

log() { printf '\n[leadpilot] %s\n' "$*"; }
die() { printf '\n[leadpilot] ERROR: %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Usage: sudo bash scripts/install-docker-ubuntu.sh

Installs Docker Engine, the Docker Compose plugin, and UFW on a fresh Ubuntu
server. Allows OpenSSH, HTTP (80/tcp), and HTTPS (443/tcp and 443/udp), then
enables the firewall. Safe to run again.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi
if [[ $# -gt 0 ]]; then
  die "Unknown argument: $1 (see --help)"
fi
[[ "$(id -u)" -eq 0 ]] || die "Run as root: sudo bash scripts/install-docker-ubuntu.sh"
[[ -r /etc/os-release ]] || die "Cannot identify this operating system."
# shellcheck disable=SC1091
. /etc/os-release
[[ "${ID:-}" == "ubuntu" ]] || die "This installer supports Ubuntu (found ${ID:-unknown})."
major="${VERSION_ID%%.*}"
[[ "${major}" -ge 22 ]] || die "Ubuntu 22.04 or newer is required (found ${VERSION_ID:-unknown})."

export DEBIAN_FRONTEND=noninteractive
codename="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"
[[ -n "$codename" ]] || die "Could not determine the Ubuntu codename."

log "Installing Docker Engine and the Compose plugin"
apt-get update
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
cat > /etc/apt/sources.list.d/docker.list <<EOF
deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${codename} stable
EOF
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

if command -v systemctl >/dev/null 2>&1 && [[ -d /run/systemd/system ]]; then
  systemctl enable --now docker
else
  die "systemd is not running, so Docker was installed but not started."
fi
docker compose version >/dev/null 2>&1 || die "Docker Compose plugin is not available."

if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
  usermod -aG docker "${SUDO_USER}"
  log "Added ${SUDO_USER} to the docker group. Log in again before using docker without sudo."
fi

log "Allowing SSH, HTTP, and HTTPS in UFW, then enabling the firewall"
apt-get install -y ufw
ufw allow OpenSSH
ufw allow 22/tcp
ssh_port="$(awk '/^[[:space:]]*Port[[:space:]]+/ {print $2; exit}' /etc/ssh/sshd_config 2>/dev/null || true)"
if [[ -n "${ssh_port}" && "${ssh_port}" != "22" ]]; then
  ufw allow "${ssh_port}/tcp"
fi
if [[ -d /etc/ssh/sshd_config.d ]]; then
  while read -r extra_port; do
    [[ -n "${extra_port}" && "${extra_port}" != "22" ]] || continue
    ufw allow "${extra_port}/tcp"
  done < <(awk '/^[[:space:]]*Port[[:space:]]+/ {print $2}' /etc/ssh/sshd_config.d/*.conf 2>/dev/null || true)
fi
ufw allow 80/tcp comment 'LeadPilot HTTP'
ufw allow 443/tcp comment 'LeadPilot HTTPS'
ufw allow 443/udp comment 'LeadPilot HTTP/3'
ufw --force enable
ufw status verbose

log "Docker is ready"
docker --version
docker compose version
echo "Next: clone LeadPilot, create .env, then run: docker compose up -d --build"
echo "The full procedure is in DOCKER.md."
