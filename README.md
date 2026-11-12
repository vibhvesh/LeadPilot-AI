# CanberraAI Lead Generation System for TMS LLC

**Product:** CanberraAI Lead Generation System  
**Customer / operating brand:** TMS LLC  
**Repository:** LeadPilot-AI

An independent recruitment-sales intelligence and team collaboration platform. Its first market focus is the United States, with India as a secondary market.

## Version 1 foundation
- FastAPI service and PostgreSQL persistence
- Lead pipeline, notes, assignment fields and AI-feedback records
- Docker Compose single-server deployment on TCP 1102
- Basic health and admin overview APIs

## Install
Requires Ubuntu with Docker Engine and Docker Compose plugin installed.

```bash
curl -fsSL https://raw.githubusercontent.com/vibhvesh/LeadPilot-AI/main/scripts/install.sh | sudo bash
```

Local health check: `curl http://127.0.0.1:1102/health`

API documentation: `http://127.0.0.1:1102/docs` (on the server).

## Credentials
The installer generates a random PostgreSQL password and temporary admin API key in `/opt/leadpilot-ai/.env`. Retrieve them on the server with:

```bash
sudo grep -E '^(DB_PASSWORD|ADMIN_API_KEY)=' /opt/leadpilot-ai/.env
```

Do not paste these secrets into chat or commit `.env` to GitHub. If lost, rotate them on the server and recreate the app container; coordinate a database password change before changing the database credential.

## Release status
This repository is the initial development scaffold, not a completed production Version 1. Google/Microsoft OIDC, full role-based access, browser dashboard, automated lead discovery providers, audit logging, database migrations, HTTPS reverse proxy and tested backup/restore remain to be implemented before production use. Do not expose the development API publicly.
