# CanberraAI LeadPilot

LeadPilot (TMS-LEAD) is the LinkTMS lead workspace. The browser UI keeps the demo’s sections — dashboard, leads, pipeline, follow-ups, team, reports, GrokBot, user administration, search, API keys, AI routing, geographic targeting, activity, comments, and settings — and those sections now read and write a real database.

GitHub Pages cannot run this service. The FastAPI app serves both the API and the UI. The Pages site can stay up as the old static preview.

## Architecture

| Module | Responsibility |
|---|---|
| `app/auth` | Google OpenID Connect and local demo sign-in. Opaque session cookies, stored hashed. |
| `app/users` | Approval, Admin / Member roles, per-module view and manage permissions. |
| `app/leads` | Lead records and the human review step that sets **Qualified**. |
| `app/search` | Saved target profiles, web search, normalization, deduplication. |
| `app/agents` | Orchestrator, research, enrichment, qualification, outreach draft, quality. |
| `app/providers` | Encrypted provider keys, role quotas, xAI / Gemini / OpenAI clients. |
| `app/audit` | Sign-ins, searches, model calls, and permission changes. |
| `app/dashboard` | Counts for the overview, pipeline, and reports. |

`vibhvesh@gmail.com` is the Super Admin and always has every module. A new Google account is stored as **pending** and gets no session until an Admin or the Super Admin approves them. Default Member access covers the lead workspace (dashboard, leads, pipeline, follow-ups, team, reports, GrokBot, search, geo, comments) and not user administration, API keys, activity, or workspace settings. Those defaults can be changed; every API route checks the stored permission.

Search uses Tavily or Brave when a key exists, otherwise a built-in demo source. LLM routing on **Auto** uses the first configured xAI, Gemini, or OpenAI key, otherwise a deterministic demo model. Outreach is stored as a draft. There is no send action. A lead becomes Qualified only through review.

## Run locally in demo mode

No Google client or provider key is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 and choose **Super Admin demo**.

Try the product:

1. Open **Search criteria**, name a profile (for example industry `logistics`, country `United States`), and choose **Save and run search**. New leads appear under **Leads**. Run it again and the same companies are skipped.
2. Open **GrokBot**, pick a lead, and run the specialist agents. The score and email draft are saved. The status stays New.
3. Choose **Mark qualified**. The pipeline and dashboard counts change.
4. Sign out, continue as another email, and confirm the pending screen. Sign back in as the Super Admin, open **Users**, and approve that account. Sign in as the new user and confirm **Users** and **API keys** are refused.

`DEMO_MODE=true` is only for a machine you control. `render.yaml` and the VPS bootstrap set it to false.

## Tests

```bash
pytest
```

The tests use an in-memory database and the demo sign-in. They cover approval, permission enforcement, search deduplication, the qualification gate, encrypted key storage, and quotas.

## Google sign-in

1. In Google Cloud Console, configure the OAuth consent screen. Add the Super Admin and any tester while the app is in Testing.
2. Create an OAuth client ID of type **Web application**.
3. Add this authorized redirect URI, exactly:
   - Local: `http://localhost:8000/auth/google/callback`
   - Production: `https://YOUR-HOST/auth/google/callback`
4. Put the client id and secret in the server environment as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. Set `PUBLIC_BASE_URL` to the same origin (no trailing path). `GOOGLE_REDIRECT_URI` overrides the callback if you need a different path.
5. Restart the app. The sign-in page shows **Sign in with Google**.

The app requests `openid email profile`, requires a verified email, and does not put the Google tokens in the browser. Sessions expire after `SESSION_MAX_AGE_SECONDS` (8 hours by default).

## Provider keys

Set any of these in the environment, or paste them in **API keys** (admins only). Pasted keys are encrypted with `ENCRYPTION_KEY` (or `SESSION_SECRET` if that is unset) and only a last-four hint is returned to the browser.

| Variable | Used for |
|---|---|
| `XAI_API_KEY` | Grok / xAI chat completions. Default model `XAI_MODEL` (`grok-3`). |
| `GEMINI_API_KEY` | Gemini. Default model `GEMINI_MODEL`. |
| `OPENAI_API_KEY` | OpenAI. Default model `OPENAI_MODEL`. |
| `TAVILY_API_KEY` | Tavily web search. |
| `BRAVE_API_KEY` | Brave web search. |
| `SEARCH_API_KEY` | Used as the Tavily key when `SEARCH_PROVIDER` is `auto` or `tavily`, or as the Brave key when `SEARCH_PROVIDER` is `brave`. |

Environment values win over a key saved in the database. On **AI / LLM**, leave the provider on **Auto** to pick the first real key, or pin xAI, Gemini, or OpenAI. Quotas for each provider and role are edited under **API keys**. A pipeline completion and a search each count as one use.

Web search results often have a company and a URL but no email or phone. Those fields are filled only when they are present in the result. The demo source includes sample contact details so the flow can be tried immediately.

## Deploy on Render

`render.yaml` defines a Python web service and a Postgres database. Free Render Postgres expires after 30 days; change the database plan in the Blueprint if this should stay up.

1. In the Render dashboard, create a Blueprint from this repository.
2. When the service has a URL, set `PUBLIC_BASE_URL` to that URL (`https://…onrender.com`).
3. Create the Google OAuth client with redirect `https://YOUR-SERVICE.onrender.com/auth/google/callback`, then set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
4. Optionally set `XAI_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `TAVILY_API_KEY`, or `BRAVE_API_KEY`.
5. Deploy again if you changed env vars that are read only at boot. Sign in as `vibhvesh@gmail.com`.

`DEMO_MODE` is false on Render, so there is no demo sign-in until Google is configured. The health check is `GET /health`.

## Existing VPS

The Ubuntu bootstrap in `bootstrap.sh` still installs Docker, writes `/opt/leadpilot-ai/.env`, and starts Compose behind Caddy for `https://leads.canberravision.com`. It now turns demo mode off and generates `ENCRYPTION_KEY`. Add the Google client to that `.env` and restart:

```bash
cd /opt/leadpilot-ai && docker compose up -d --build
```

Details remain in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). An existing database from the earlier preview is kept; new columns are added on startup. If that database was only sample API data and you want a clean schema, take a backup and recreate the `leadpilot_db` volume before relying on it.

## Security notes

- Do not commit `.env`, OAuth secrets, or provider keys.
- Set `DEMO_MODE=false` and `SESSION_COOKIE_SECURE=true` whenever the app is on the public internet.
- Super Admin cannot be demoted from the users screen. Only the Super Admin can grant Admin or edit role templates.
- Provider keys are not rendered into HTML or returned by the API.
