# LeadPilot in Docker

The Compose stack runs the FastAPI app, Postgres 16, and Caddy. One command recreates those processes on a server that already has Docker and a `.env` file:

```bash
docker compose up -d --build
```

`deploy/install.sh` is the non-Docker install (systemd, host Postgres, host nginx). It is unchanged. Local `uvicorn` and `pytest` are unchanged. Compose overrides `DATABASE_URL` so the container uses the Postgres service even when `.env` still points at the SQLite file used for local demo mode.

The app container listens on port 1102 and is published only on `127.0.0.1`. Caddy is the public listener. Postgres is not published to the host.

## Fresh Ubuntu server

1. Clone the repository and install Docker, the Compose plugin, and UFW. The firewall allows SSH, TCP 80, TCP 443, and UDP 443.

   ```bash
   sudo apt-get update
   sudo apt-get install -y git
   sudo git clone https://github.com/vibhvesh/LeadPilot-AI.git /opt/leadpilot-ai
   cd /opt/leadpilot-ai
   sudo bash scripts/install-docker-ubuntu.sh
   ```

   The install script adds the user who invoked `sudo` to the `docker` group. Until that user logs in again, run Compose with `sudo`.

2. Create the env file and replace every placeholder. `openssl rand -hex 32` is a session secret. `openssl rand -hex 24` is a database password. Set `DEMO_MODE=false` and `APP_ENV=production` before the server is reachable.

   ```bash
   cp .env.example .env
   chmod 600 .env
   ```

3. Choose HTTP or HTTPS, then start the stack.

   HTTP, by IP or before DNS exists:

   ```bash
   # in .env
   TLS_MODE=http
   LEADPILOT_DOMAIN=
   LEADPILOT_BIND=0.0.0.0
   PUBLIC_BASE_URL=http://YOUR_SERVER_IP
   SESSION_COOKIE_SECURE=false
   ```

   Automatic HTTPS after the DNS A record points at this server. Also allow ports 80 and 443 on the cloud firewall. Caddy requests the certificate by itself.

   ```bash
   # in .env
   TLS_MODE=https
   LEADPILOT_DOMAIN=leads.example.com
   ACME_EMAIL=you@example.com
   LEADPILOT_BIND=0.0.0.0
   PUBLIC_BASE_URL=https://leads.example.com
   SESSION_COOKIE_SECURE=true
   GOOGLE_REDIRECT_URI=https://leads.example.com/auth/google/callback
   ```

   `TLS_MODE=auto` uses HTTPS when `LEADPILOT_DOMAIN` is a hostname and HTTP when it is empty, `localhost`, or an IP.

4. Build and start:

   ```bash
   docker compose up -d --build
   curl -fsS http://127.0.0.1:1102/health
   ```

   In HTTP mode the login page is `http://YOUR_SERVER_IP/login`. In HTTPS mode it is `https://LEADPILOT_DOMAIN/login`.

Useful checks:

```bash
docker compose ps
docker compose logs -f app
docker compose logs --tail=100 proxy
```

## Move an existing systemd server

The current host install is `leadpilot.service`, env file `/etc/leadpilot/leadpilot.env`, and the distro Postgres database `leadpilot`. The app port on that host is whatever `ExecStart` uses (1102 on the existing server, 8000 if the installer default was left in place). Keep that server running until the new one has been checked. Lower the DNS TTL before the cutover.

On the old server, stop the app so the dump is not missing writes, and leave Postgres running:

```bash
sudo systemctl stop leadpilot
sudo -u postgres pg_dump -Fc --no-owner --no-acl leadpilot > /root/leadpilot.dump
sudo cp /etc/leadpilot/leadpilot.env /root/leadpilot.env
sudo tar -C /root -czf /root/leadpilot-migrate.tar.gz leadpilot.dump leadpilot.env
sudo chmod 600 /root/leadpilot-migrate.tar.gz
```

If this repository is already checked out on the old server, `sudo bash scripts/backup.sh --source systemd` writes the same kind of archive under `backups/`.

Copy the archive to the new server with `scp` or `rsync`. Do not commit it.

On the new server, install Docker as in the fresh-install section. Create `.env` from `.env.example` and set:

- `DB_PASSWORD` to a new password for the container database. The dump does not reuse the old role password.
- `SESSION_SECRET` and `ENCRYPTION_KEY` to the exact values from `/etc/leadpilot/leadpilot.env`. Saved provider keys cannot be decrypted with a different encryption key. Existing browser sessions also depend on `SESSION_SECRET`.
- The same `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, search keys, model keys, `X_API_KEY`, and `GROKBOT_WEBHOOK_SECRET` as the old file.
- `SUPER_ADMIN_EMAIL` to the same address.
- `DEMO_MODE=false` and `APP_ENV=production`.
- HTTP values first (`TLS_MODE=http`, `SESSION_COOKIE_SECURE=false`, `PUBLIC_BASE_URL=http://NEW_IP`) so you can test before DNS changes.

Compose always points the app at the `db` service. You do not copy the old `DATABASE_URL` (`127.0.0.1`) into the running container.

Load the dump, then check the site by IP:

```bash
cd /opt/leadpilot-ai
bash scripts/restore.sh /root/leadpilot-migrate.tar.gz
curl -fsS http://127.0.0.1:1102/health
curl -fsS http://127.0.0.1/login
```

`restore.sh` refuses to replace a database that already has tables. After a rehearsal, run `bash scripts/restore.sh --force /root/leadpilot-migrate.tar.gz`. `--force` drops `schema public` inside the container database. It does not delete the `leadpilot_db` volume.

Sign in over HTTP and confirm a lead you know is present. Then set the HTTPS values, run `docker compose up -d` again, and point the DNS A record at the new server. Watch `docker compose logs proxy` until Caddy finishes the certificate. The Google OAuth client needs the new redirect URI if the hostname changed.

When HTTPS works, the old host can stay powered on and stopped (`leadpilot` remains stopped) until you are ready to remove it. Start it again only as a rollback, not while both servers are accepting writes.

The container database is Postgres 16. A dump from Postgres 16 or older restores. Ubuntu 22.04's package is 14 and Ubuntu 24.04's package is 16, so a host installed by `deploy/install.sh` is in range.

## Updating

Take a backup first. Schema changes run when the app starts: new tables are created and new columns are added. Existing rows are kept.

```bash
cd /opt/leadpilot-ai
bash scripts/backup.sh
git pull --ff-only
docker compose up -d --build
curl -fsS http://127.0.0.1:1102/health
```

## Backups

`bash scripts/backup.sh` writes `backups/leadpilot-YYYYMMDDTHHMMSSZ.tar.gz` (mode 600). The archive contains a custom-format `pg_dump`, a copy of `.env`, and a manifest. On a host where the Compose database is not running, the same script dumps the systemd database and copies `/etc/leadpilot/leadpilot.env`.

```bash
bash scripts/backup.sh --source docker
sudo bash scripts/backup.sh --source systemd
```

Copy the archives off the server. `backups/` is gitignored. A database backup without the matching `SESSION_SECRET` and `ENCRYPTION_KEY` cannot reopen encrypted provider keys.

Restore a later archive into Compose with:

```bash
bash scripts/restore.sh --force backups/leadpilot-YYYYMMDDTHHMMSSZ.tar.gz
```

## Rollback

Application rollback is the previous git revision, then a rebuild:

```bash
cd /opt/leadpilot-ai
bash scripts/backup.sh
git checkout <previous-revision>
docker compose up -d --build
curl -fsS http://127.0.0.1:1102/health
```

Database rollback is a backup archive and `scripts/restore.sh --force`. Do not delete the `leadpilot_db` volume to undo a deploy. `docker compose down` stops the containers and keeps the volume. `docker compose down -v` deletes the database and the certificates.

DNS rollback, during a migration, is pointing the A record back at the old server and starting the old service:

```bash
sudo systemctl start leadpilot
```

Do that only if the new server is no longer taking writes. The two databases diverge as soon as someone uses either one.

## Layout

| Path | Role |
|---|---|
| `Dockerfile` | Python 3.12 slim image, non-root user, `GET /health` check |
| `docker-compose.yml` | app, Postgres volume, Caddy |
| `deploy/proxy/entrypoint.sh` | HTTP or automatic HTTPS from `TLS_MODE` |
| `.env.example` | every variable the app reads, plus the Compose settings |
| `scripts/install-docker-ubuntu.sh` | Docker, Compose, and UFW on Ubuntu 22.04+ |
| `scripts/backup.sh` | timestamped dump and env archive |
| `scripts/restore.sh` | load a dump into the Compose database |

`bootstrap.sh` still targets `leads.canberravision.com` and now sets `TLS_MODE=https` so that existing one-shot bootstrap keeps requesting a certificate.
