# CanberraAI Lead Generation System for TMS LLC

**Product:** CanberraAI LeadPilot  
**Initial workspace:** LinkTMS  
**Repository:** LeadPilot-AI

## Deployment hostname

Planned public hostname: **https://leads.canberravision.com**

Create this DNS record when ready:

| Type | Host | Value |
|---|---|---|
| A | leads | 130.250.191.136 |

The Nginx reverse proxy listens on TCP 80 and forwards requests for this hostname to the FastAPI app on port 1102. After DNS resolves to the VPS, configure HTTPS before enabling OAuth or sharing real data.

## Deploy updates on the VPS

```bash
cd /opt/leadpilot-ai && git pull --ff-only origin main && docker compose up -d --build
```

Check:

```bash
docker compose ps
curl -i http://127.0.0.1:1102/health
```

## Current release status

The dashboard is a navigation-enabled visual preview with sample records. The Leads, Follow-ups, Team and Settings sections are explanatory placeholders. Live lead CRUD is available only through development API endpoints protected by a temporary shared admin key. Google Workspace OIDC, verified domain onboarding, individual user approval, company-scoped RBAC, production session security, migrations, audit logging and HTTPS are not implemented yet. Do not expose the app publicly or enter real customer/candidate data until these controls are completed.

## Google Workspace plan

Target domain: `linktms.com`  
Initial tester: `shailesh@linktms.com`  
Google callback after HTTPS is configured: `https://leads.canberravision.com/auth/google/callback`

Google OAuth client secrets must be stored only in the VPS environment, never in GitHub. Email suffix alone is not sufficient proof of company membership; verify the Workspace domain and require approved membership.
