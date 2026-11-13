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

## First-time deployment

1. Install Docker Engine with the Docker Compose plugin and Git on Ubuntu.
2. Clone this repository to `/opt/leadpilot-ai`.
3. Create `.env` from `.env.example` and set strong, unique secrets. Do not commit `.env`.
4. Ensure the DNS record above resolves to the VPS and ports 80/443 are reachable.
5. Run the installer:

```bash
cd /opt/leadpilot-ai
bash install.sh
```

The installer checks root privileges, Docker Compose, the local environment file, a clean Git working tree, DNS resolution and the app health endpoint. It then fast-forward pulls `main`, validates Compose, deploys the stack and checks HTTPS.

## Update an existing installation

```bash
cd /opt/leadpilot-ai && bash install.sh
```

The installer refuses to pull if it detects uncommitted local changes. Review or stash those changes before retrying. It does not delete the PostgreSQL or Caddy data volumes.

## Useful checks

```bash
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
