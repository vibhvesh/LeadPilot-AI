# Single-server installation

Requires Ubuntu Linux with Docker Engine and Docker Compose plugin already installed.

One-line install:

```bash
curl -fsSL https://raw.githubusercontent.com/vibhvesh/LeadPilot-AI/main/scripts/install.sh | sudo bash
```

The installer clones the repository into `/opt/leadpilot-ai`, creates a random database password and temporary admin API key, and starts Docker Compose.

Health check (on server):
```bash
curl http://127.0.0.1:1102/health
```

Check services:
```bash
cd /opt/leadpilot-ai && sudo docker compose ps
```

Logs:
```bash
cd /opt/leadpilot-ai && sudo docker compose logs -f app
```

Development-only: the application binds to localhost, and the temporary admin key must be replaced by Google/Microsoft OIDC and per-user role authorization before external exposure. HTTPS, migrations, restore testing, and audit logging are not yet implemented.
