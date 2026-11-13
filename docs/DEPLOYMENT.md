# CanberraAI Lead Generation System for TMS LLC — deployment

Render deployment is described in the README (`render.yaml`: web service + Postgres). The steps below are the existing VPS installer.

Requires Ubuntu with Docker Engine and Docker Compose plugin installed.

## One-line installer

```bash
curl -fsSL https://raw.githubusercontent.com/vibhvesh/LeadPilot-AI/main/scripts/install.sh | sudo bash
```

The installer clones the repository into `/opt/leadpilot-ai`, generates a random database password and temporary admin API key, then starts Docker Compose. The application listens on localhost TCP 1102.

## Links and checks

- GitHub: https://github.com/vibhvesh/LeadPilot-AI
- Installer: https://raw.githubusercontent.com/vibhvesh/LeadPilot-AI/main/scripts/install.sh
- Local health: http://127.0.0.1:1102/health
- API docs: http://127.0.0.1:1102/docs

## Retrieve generated credentials

Run on the server:

```bash
sudo grep -E '^(DB_PASSWORD|ADMIN_API_KEY)=' /opt/leadpilot-ai/.env
```

Keep the output private. Do not commit `.env` or send credentials in chat.

## Operations

```bash
cd /opt/leadpilot-ai
sudo docker compose ps
sudo docker compose logs -f app
sudo docker compose restart
```

This is an initial development scaffold. Before production, implement Google and Microsoft OIDC, per-user RBAC, audit logs, database migrations, HTTPS reverse proxy, tested backup/restore and external security review. Do not expose the development API directly to the internet.
