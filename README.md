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
| `app/ai_search` | Natural-language search: plan, query, read pages, extract, then save leads. |
| `app/bot` | Grok Bot API tokens, deep-search requests, and the outbound webhook. |
| `app/agents` | Orchestrator, research, enrichment, qualification, outreach draft, quality. |
| `app/providers` | Encrypted provider keys, role quotas, xAI / Gemini / OpenAI clients. |
| `app/audit` | Sign-ins, searches, model calls, and permission changes. |
| `app/dashboard` | Counts for the overview, pipeline, and reports. |

`vibhvesh@gmail.com` is the Super Admin and always has every module. A new Google account is stored as **pending** and gets no session until an Admin or the Super Admin approves them. Default Member access covers the lead workspace (dashboard, leads, pipeline, follow-ups, team, reports, GrokBot, search, geo, comments) and not user administration, API keys, activity, or workspace settings. Those defaults can be changed; every API route checks the stored permission.

Search uses Tavily or Brave when a key exists. With no search key, a search returns “No search provider configured” and saves nothing. LLM routing on **Auto** uses the first configured xAI, Gemini, or OpenAI key. With no model key, research, scoring, and outreach return “No LLM provider configured”. `DEMO_MODE` only enables local sign-in. Outreach is stored as a draft. There is no send action. A lead becomes Qualified only through review.

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
| `AI_SEARCH_MAX_ROUNDS` | How many times AI search rewrites its queries when results are thin. Default `2`. |
| `GROKBOT_WEBHOOK_URL` | Optional URL that receives a deep-search request. |
| `GROKBOT_WEBHOOK_SECRET` | Optional secret sent as `X-LeadPilot-Webhook-Secret`. |
| `SEARCH_API_KEY` | Used as the Tavily key when `SEARCH_PROVIDER` is `auto` or `tavily`, or as the Brave key when `SEARCH_PROVIDER` is `brave`. |

Environment values win over a key saved in the database. On **AI / LLM**, leave the provider on **Auto** to pick the first real key, or pin xAI, Gemini, or OpenAI. Quotas for each provider and role are edited under **API keys**. A pipeline completion and a search each count as one use.

Web search results often have a company and a URL but no email or phone. Those fields are filled only when they are present in the result.

AI search has its own per-user quota (`ai_search` on the API keys page). Members start at 10 runs a day and 100 a month. Each run is written to the activity log.

## AI search

On **Search criteria**, type a request such as “hospitals in Gujarat that use walkie-talkies and might buy Boondock Echo” and choose **Run AI search**.

The planner (xAI, Gemini, or OpenAI) returns a target profile, locations, signals, and search queries. Those queries run on every configured search provider (Tavily and Brave when keys exist). The top pages are read, companies and contacts are extracted, and thin results trigger another round up to `AI_SEARCH_MAX_ROUNDS`. New rows are deduplicated, enriched, and scored, then saved as leads with source `ai-search`. The plan and source URLs stay on the search page. Without a model key or a search key, the page shows that error and saves no leads.

**Deep search with Grok Bot** uses the same text, stores a `pending` request, and POSTs this JSON to `GROKBOT_WEBHOOK_URL` when that variable is set:

```json
{
  "request_id": 1,
  "text": "hospitals in Gujarat that might buy Boondock Echo",
  "plan": {"profile": "...", "locations": [], "signals": [], "queries": []},
  "callback_base_url": "https://YOUR-HOST"
}
```

If `GROKBOT_WEBHOOK_SECRET` is set, it is sent as the header `X-LeadPilot-Webhook-Secret`. The request is still saved when the webhook is missing or the call fails.

## Grok Bot API

An admin creates a token under **Settings → Grok Bot tokens**. The raw token is shown once and only its hash is stored. Send it as `Authorization: Bearer lpb_...`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/bot/requests?status=pending` | List requests. `status` is `pending`, `claimed`, `completed`, or `all`. |
| `POST` | `/api/bot/requests/{id}/claim` | Mark a pending request claimed. |
| `POST` | `/api/bot/requests/{id}/complete` | Body `{"notes": "..."}`. Marks the request completed. |
| `POST` | `/api/bot/leads` | Bulk-create leads for a request. |

Lead body:

```json
{
  "request_id": 1,
  "leads": [
    {
      "company": "Echo Buyer Hospital",
      "contact_name": "Meera Shah",
      "email": "meera@echobuyer.example",
      "phone": "+91-79-5555-0199",
      "website": "https://echobuyer.example",
      "city": "Ahmedabad",
      "state": "Gujarat",
      "country": "India",
      "industry": "healthcare",
      "why_fit": "Uses handheld radios.",
      "source_url": "https://echobuyer.example/about"
    }
  ]
}
```

`company` is required. The server forces `source` to `grokbot`, links `deep_search_request_id`, skips duplicates, and scores the new leads. At most 50 leads per call. The search page shows how many leads came from the app and how many came from Grok Bot.

## Talk to Bots

A bot with an API token can ask to chat. `POST /api/bot/connect` creates a pending connection:

```json
{
  "name": "Grok Bot",
  "description": "Finds and explains leads",
  "avatar_url": "https://example.com/avatar.png",
  "webhook_url": "https://bot.example/talk",
  "user_email": "person@company.com"
}
```

`avatar_url`, `webhook_url`, and `user_email` are optional. `user_email` addresses one approved user, who can approve, block, or revoke that request. Without it, only an Admin or Super Admin can decide. Approve, block, and revoke are written to the activity log.

The **Bots** page lists pending, approved, and blocked bots and polls unread counts. An approved bot has one thread.

| Method | Path | Who | Purpose |
|---|---|---|---|
| `POST` | `/api/bot/connect` | Bot token | Register or update the connection. |
| `GET` | `/api/bot/messages?since=` | Bot token | Messages newer than an id or ISO time. `403` until approved. |
| `POST` | `/api/bot/messages` | Bot token | Send `{text, cards}`. `403` until approved. |
| `GET` | `/api/bots` | Signed-in user | Connections that person can see. |
| `GET` | `/api/bots/unread` | Signed-in user | `{unread: N}` for the nav badge. |
| `POST` | `/api/bots/{id}/decision` | Signed-in user | `{"decision": "approve"\|"block"\|"revoke"}`. |
| `GET` | `/api/bots/{id}/messages` | Signed-in user | Thread. Marks bot messages read. |
| `POST` | `/api/bots/{id}/messages` | Signed-in user | `{"text": "hello"}`. |

A bot reply can include cards. A lead card looks like this:

```json
{
  "text": "Three hospitals worth a look",
  "cards": [
    {
      "type": "leads",
      "title": "Suggested leads",
      "leads": [
        {"company": "City Hospital", "email": "desk@city.example", "city": "Ahmedabad", "state": "Gujarat", "country": "India"}
      ]
    }
  ]
}
```

The chat shows **Add to pipeline** on each lead. That calls the normal lead create API. If the bot registered `webhook_url`, each user message is also POSTed there as `{connection_id, message_id, text, sender, callback_base_url}`. `GROKBOT_WEBHOOK_SECRET`, when set, is sent as `X-LeadPilot-Webhook-Secret`. A failed webhook does not block the chat message.

Agent prompts and the outreach draft use **Settings → Business profile** (company name, what you sell, ideal customer). Until that is changed, the text stays the LinkTMS staffing pitch.

## Install on a fresh Ubuntu or Debian server

`deploy/install.sh` installs nginx, PostgreSQL, uv, and Python 3.12, then runs LeadPilot as the `leadpilot` user under systemd. It is safe to run again: keys already present in `/etc/leadpilot/leadpilot.env` are left as they are, and only missing keys are added.

```bash
curl -fsSL https://raw.githubusercontent.com/vibhvesh/LeadPilot-AI/main/deploy/install.sh | sudo bash
```

Pass flags after `-s --` when stdin is the script:

```bash
curl -fsSL https://raw.githubusercontent.com/vibhvesh/LeadPilot-AI/main/deploy/install.sh | sudo bash -s -- \
  --domain leads.example.com \
  --email admin@example.com \
  --super-admin vibhvesh@gmail.com \
  --demo-mode false \
  --google-client-id YOUR_CLIENT_ID \
  --google-client-secret YOUR_CLIENT_SECRET
```

Optional flags: `--xai-api-key`, `--gemini-api-key`, `--openai-api-key`, `--tavily-api-key`, `--brave-api-key`, `--search-api-key`, `--grokbot-webhook-url`, `--grokbot-webhook-secret`.

From a checkout: `sudo bash deploy/install.sh` with the same flags. HTTPS is requested only when `--domain` is set, an email is available, and the domain resolves to this machine. If there is no global IPv6 route, IPv6 is disabled so outbound calls (Google sign-in, provider APIs) do not hang on an unreachable AAAA address.

```bash
sudo bash deploy/install.sh --upgrade      # pull main, install deps, apply schema, restart
sudo bash deploy/install.sh --uninstall    # remove systemd and nginx, keep data
sudo bash deploy/install.sh --uninstall --purge
```

The app listens on `127.0.0.1:8000` with one worker. nginx is the public listener. Schema updates run when the service starts and again during `--upgrade`.

The older `bootstrap.sh` path (Docker and Caddy on a fixed host) is still in the repository. Use `deploy/install.sh` for a normal Ubuntu or Debian VPS.

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
