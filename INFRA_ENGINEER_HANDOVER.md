# LeadPilot AI V2 — Infrastructure Engineer Handover

**Repository:** https://github.com/vibhvesh/LeadPilot-AI  
**Deployment target:** Fresh Ubuntu VPS using Docker Compose  
**Application:** FastAPI + PostgreSQL 16 + Caddy reverse proxy  
**Recommended OS:** Ubuntu 24.04 LTS (the Docker installer supports Ubuntu 22.04+)  
**Primary deployment guide:** `DOCKER.md`

This handover describes the current code in the `main` branch. The application code and Docker deployment files are already present in the repository. This document is the operational checklist for the infrastructure engineer.

## 1. Important architecture facts

The current Compose stack contains three services:

- `app`: LeadPilot FastAPI application (Python 3.12), published only on host loopback port 1102.
- `db`: PostgreSQL 16, on an internal Docker network with a persistent named volume.
- `proxy`: Caddy reverse proxy for HTTP and automatic HTTPS.

**Redis is not currently a service in the checked-in `docker-compose.yml`.** Do not assume Redis is installed or required by this deployment. The application is modularized in the FastAPI codebase; the current production Compose topology is the three services above.

The GitHub Pages site is a static showcase only. GitHub Pages cannot run the API or database. The real V2 application is served by the FastAPI container.

## 2. Before installation

Confirm the following with the project owner:

- A fresh Ubuntu 22.04+ VPS is available; Ubuntu 24.04 LTS is recommended.
- A DNS A record for the chosen application hostname points to the VPS public IPv4 address.
- The cloud/provider firewall allows inbound TCP 22 (or the configured SSH port), TCP 80 and TCP 443. UDP 443 is optional for HTTP/3.
- The engineer has SSH/root or sudo access.
- The production hostname and ACME contact email are known.
- Google OAuth credentials are available if Google sign-in is required.
- AI/search provider API keys are available if those features are to be enabled.

Do not copy secrets into GitHub, this document, tickets, screenshots or chat.

## 3. Clone the repository and install Docker

Run the following as root, or enter a root shell with `sudo -i` first:

```bash
apt-get update
apt-get install -y git
git clone https://github.com/vibhvesh/LeadPilot-AI.git /opt/leadpilot-ai
cd /opt/leadpilot-ai
bash scripts/install-docker-ubuntu.sh
```

The installer installs Docker Engine, the Docker Compose plugin and UFW. It allows SSH, HTTP and HTTPS before enabling UFW. Review the resulting firewall rules and confirm the provider-level firewall also allows the required ports.

Verify:

```bash
docker --version
docker compose version
ufw status verbose
```

## 4. Create the production environment file

```bash
cd /opt/leadpilot-ai
cp .env.example .env
chmod 600 .env
nano .env
```

Set the following values. Replace the example hostname and email with the values approved for this deployment.

### Required production settings

```dotenv
DEMO_MODE=false
APP_ENV=production
SUPER_ADMIN_EMAIL=owner@example.com

POSTGRES_USER=leadpilot
POSTGRES_DB=leadpilot

TLS_MODE=https
LEADPILOT_DOMAIN=leads.example.com
ACME_EMAIL=infra@example.com
LEADPILOT_BIND=0.0.0.0
LEADPILOT_HTTP_PORT=80
LEADPILOT_HTTPS_PORT=443
LEADPILOT_APP_PORT=1102

PUBLIC_BASE_URL=https://leads.example.com
SESSION_COOKIE_SECURE=true
GOOGLE_REDIRECT_URI=https://leads.example.com/auth/google/callback
```

Generate three different secrets on the server. Run each command separately and place its output into the matching variable in `.env`. Do not use the same value for multiple variables.

```bash
openssl rand -hex 24   # DB_PASSWORD
openssl rand -hex 32   # SESSION_SECRET
openssl rand -hex 32   # ENCRYPTION_KEY
```

Set:

- `DB_PASSWORD` to the first generated value.
- `SESSION_SECRET` to the second generated value.
- `ENCRYPTION_KEY` to the third generated value.

Keep `SESSION_SECRET` and `ENCRYPTION_KEY` stable after deployment. Changing them can invalidate sessions and make provider keys previously encrypted by the application unreadable. Keep a protected backup of the `.env` file together with database backups.

### Google sign-in

For production, `DEMO_MODE=false` disables the local demo sign-in. If users are to sign in with Google:

1. Configure the OAuth consent screen in Google Cloud Console.
2. Create an OAuth client of type **Web application**.
3. Add the exact authorized redirect URI: `https://YOUR_DOMAIN/auth/google/callback`.
4. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in the server's `.env`.
5. Set `PUBLIC_BASE_URL` and `GOOGLE_REDIRECT_URI` to the production hostname.
6. Ensure `SUPER_ADMIN_EMAIL` matches the verified Google account that should receive Super Admin access.

Do not put Google client secrets in frontend code or GitHub Pages.

### Optional AI and search providers

The application can start without provider keys, but live research and AI functions that depend on those providers will report that no provider is configured. Add only the keys the owner has approved:

- `XAI_API_KEY`
- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `TAVILY_API_KEY` and/or `BRAVE_API_KEY`
- Optional `X_API_KEY` (read-only public-post access)
- Optional `GROKBOT_WEBHOOK_URL` and `GROKBOT_WEBHOOK_SECRET`

Provider keys can also be configured through the application’s admin-only API keys page. Environment values take precedence over database-stored values.

## 5. Validate and start the stack

First confirm DNS resolves to this server:

```bash
getent ahostsv4 leads.example.com
```

Then validate Compose and start the application:

```bash
cd /opt/leadpilot-ai
docker compose config -q
docker compose up -d --build
```

Check containers and application health:

```bash
docker compose ps
curl -fsS http://127.0.0.1:1102/health
docker compose logs --tail=100 app
docker compose logs --tail=100 db
docker compose logs --tail=100 proxy
```

The public URL should be:

```text
https://leads.example.com/login
```

Caddy obtains and renews the HTTPS certificate automatically when DNS and inbound ports 80/443 are correct. If certificate issuance fails, inspect the proxy logs and provider firewall before changing application settings.

## 6. First application checks

- Open the production HTTPS URL.
- Confirm the login page loads and the browser shows a valid HTTPS certificate.
- Complete Google sign-in using an approved account (if Google OAuth is configured).
- Confirm the configured Super Admin account receives Super Admin access.
- Test a non-admin account: it should remain pending until approved.
- Confirm a Member cannot access User Administration, API Keys, Activity or Workspace Settings unless those permissions are explicitly granted.
- Verify that a lead can be created/reviewed and that the qualification gate works.
- Verify search/AI features only after the required provider keys are configured.

Do not use `DEMO_MODE=true` on an internet-accessible production server.

## 7. Backups and updates

Take a backup before every deployment:

```bash
cd /opt/leadpilot-ai
bash scripts/backup.sh
git pull --ff-only origin main
docker compose up -d --build
curl -fsS http://127.0.0.1:1102/health
docker compose ps
```

Backups are written under `backups/` with restrictive permissions. Copy backup archives to secure off-server storage. The archive includes the database dump and environment file; treat it as highly sensitive.

To restore an archive into the Compose database:

```bash
bash scripts/restore.sh backups/leadpilot-YYYYMMDDTHHMMSSZ.tar.gz
```

The restore script refuses to overwrite a populated database unless `--force` is explicitly supplied. **A forced restore replaces the public schema. Confirm the target and backup before using it.**

Never run `docker compose down -v` as a routine update or rollback: `-v` deletes named volumes, including the database and Caddy certificate data.

## 8. Useful operations

```bash
cd /opt/leadpilot-ai

# Status
docker compose ps

# Follow application logs
docker compose logs -f app

# Proxy logs
docker compose logs -f proxy

# Restart the stack
docker compose restart

# Stop containers without deleting persistent volumes
docker compose down

# Start after a stop
docker compose up -d
```

## 9. Important notes about existing scripts

- `DOCKER.md` is the detailed Docker deployment and migration guide.
- `scripts/install-docker-ubuntu.sh` installs Docker, Compose and UFW; it does not clone or deploy the application.
- `install.sh` is an existing-server deploy/update script. It expects an existing checkout and `.env`, and it checks a configured DNS/IP pair.
- `bootstrap.sh` is a fresh-server bootstrap currently hard-coded to `leads.canberravision.com` and an expected IPv4 address. **Do not run it for a different hostname or server IP without first reviewing and changing those constants.** The manual procedure in this handover and `DOCKER.md` is the safer generic path.

## 10. Handover completion checklist

- [ ] Ubuntu version and server access confirmed.
- [ ] DNS A record and provider firewall confirmed.
- [ ] Docker Engine, Compose and UFW installed.
- [ ] Production `.env` created with unique secrets and mode 600.
- [ ] `DEMO_MODE=false` and `APP_ENV=production`.
- [ ] Google OAuth configured, if required.
- [ ] Compose stack started and all services healthy.
- [ ] HTTPS certificate valid.
- [ ] Super Admin sign-in and permission checks passed.
- [ ] Backup created and copied off-server.
- [ ] Owner receives hostname, deployment commit, service status and backup location (never the secret values).

## Repository references

- Repository: https://github.com/vibhvesh/LeadPilot-AI
- Docker guide: https://github.com/vibhvesh/LeadPilot-AI/blob/main/DOCKER.md
- Environment template: https://github.com/vibhvesh/LeadPilot-AI/blob/main/.env.example
- Compose stack: https://github.com/vibhvesh/LeadPilot-AI/blob/main/docker-compose.yml
- Docker installer: https://github.com/vibhvesh/LeadPilot-AI/blob/main/scripts/install-docker-ubuntu.sh
