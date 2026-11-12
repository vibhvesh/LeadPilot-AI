# LeadPilot AI

Independent recruitment sales lead-management platform.

## Development milestone 1
FastAPI API, PostgreSQL, lead tracking, notes, feedback and basic admin controls. Runs on port **1102** with Docker Compose.

**Security:** This is a development scaffold, not a production deployment. The API is bound to localhost by default; implement Google/Microsoft OIDC and role-based authorization before public exposure.

## Start
```bash
git clone https://github.com/vibhvesh/LeadPilot-AI.git
cd LeadPilot-AI
cp .env.example .env
# Change DB_PASSWORD and ADMIN_API_KEY in .env to strong random values
docker compose up -d --build
curl http://127.0.0.1:1102/health
```

API docs: http://127.0.0.1:1102/docs

Next milestones: Google/Microsoft sign-in, RBAC, lead discovery adapters, browser dashboard, audit logs, migrations, backups, and secure deployment.
