# CanberraAI Lead Generation System for TMS LLC

**Product:** CanberraAI LeadPilot  
**Initial workspace:** LinkTMS  
**Repository:** LeadPilot-AI

## Production hostname and DNS

Hostname: **https://leads.canberravision.com**

Create this DNS record:

| Type | Host | Value |
|---|---|---|
| A | leads | 130.250.191.136 |

Allow inbound TCP ports **80 and 443** in the VPS/provider firewall. Caddy obtains and renews HTTPS certificates automatically and stores certificate state in the persistent Docker volume `caddy_data`.

## Fresh Ubuntu installation — one command

1. Install **Ubuntu 24.04 LTS** on a fresh VPS.
2. Ensure the DNS A record above resolves to the VPS public IP.
3. Allow inbound TCP ports **80 and 443** in the VPS/provider firewall.
4. Log in as root and run:

```bash
curl -fsSL https://raw.githubusercontent.com/vibhvesh/LeadPilot-AI/main/bootstrap.sh | bash
```

The bootstrap script installs base packages and Docker Engine/Compose, clones the repository to `/opt/leadpilot-ai`, generates secure environment secrets, configures the app, PostgreSQL and Caddy, starts the containers, and checks the app health endpoint and HTTPS. It refuses to overwrite an existing `/opt/leadpilot-ai` directory. It does not configure Google OAuth or implement Google Workspace login.

## Update an existing installation

After reviewing any local changes, run:

```bash
cd /opt/leadpilot-ai && git pull --ff-only origin main && bash install.sh
```

The update installer requires an existing `.env`, checks DNS and app health, validates Compose, deploys the stack and checks HTTPS. It does not delete the PostgreSQL or Caddy data volumes.

## Useful checks

```bash
cd /opt/leadpilot-ai
docker compose ps
docker compose logs --tail=100 proxy
curl -i https://leads.canberravision.com/health
```

## Current release status

The dashboard is a navigation-enabled visual preview with sample records. The Leads, Follow-ups, Team and Settings sections are explanatory placeholders. Live lead CRUD is available only through development API endpoints protected by a temporary shared admin key. Google Workspace OIDC, verified domain onboarding, individual user approval, company-scoped RBAC, production session security, migrations and audit logging are not implemented yet. Do not enter real customer/candidate data until these controls are completed.

## Google Workspace plan

Target domain: `linktms.com`  
Initial tester: `shailesh@linktms.com`  
Google callback after authentication is implemented: `https://leads.canberravision.com/auth/google/callback`

Google OAuth client secrets must be stored only in the VPS environment, never in GitHub. Email suffix alone is not sufficient proof of company membership; verify the Workspace domain and require approved membership.
