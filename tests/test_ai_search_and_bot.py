"""AI search planning, Grok Bot tokens, lead ingest, and webhook dispatch."""

import httpx

from app.ai_search.planner import fallback_plan, make_plan, normalize_plan
from app.core.config import get_settings
from tests.helpers import login


def _admin(client):
    response = login(client, "vibhvesh@gmail.com", "Vibhvesh")
    assert response.status_code == 200
    return response


def test_planner_normalizes_a_mocked_llm_plan(monkeypatch):
    class FakeLLM:
        def __init__(self, db, user):
            self.db = db

        def complete_json(self, **kwargs):
            return {
                "data": {
                    "profile": "Hospitals that may buy Boondock Echo",
                    "locations": ["Gujarat"],
                    "signals": ["walkie-talkies"],
                    "queries": ["hospitals Gujarat radios", "Boondock Echo buyers"],
                },
                "provider": "mock",
                "model": "test",
                "note": "mocked",
            }

    monkeypatch.setattr("app.ai_search.planner.LLMClient", FakeLLM)
    plan = make_plan(None, None, "hospitals in Gujarat that use walkie-talkies and might buy Boondock Echo", {})
    assert plan["profile"].startswith("Hospitals")
    assert "Gujarat" in plan["locations"]
    assert "walkie-talkies" in plan["signals"]
    assert 3 <= len(plan["queries"]) <= 8
    assert plan["queries"][0] == "hospitals Gujarat radios"
    padded = normalize_plan({"queries": ["only one"]}, "clinics in Gujarat")
    assert len(padded["queries"]) >= 3
    capped = normalize_plan({"queries": [f"query {index}" for index in range(12)]}, "clinics")
    assert len(capped["queries"]) == 8
    assert len(fallback_plan("labs").get("queries")) >= 3


def test_ai_search_saves_scored_leads_and_respects_quota(client, monkeypatch):
    _admin(client)
    first = client.post("/api/search/ai", json={"text": "hospitals in Gujarat that use walkie-talkies"})
    assert first.status_code == 200
    body = first.json()
    assert 3 <= len(body["plan"]["queries"]) <= 8
    assert body["created_count"] >= 1
    assert body["sources"]
    leads = client.get("/api/leads").json()
    created = [lead for lead in leads if lead["source"] == "ai-search"]
    assert created
    assert created[0]["score"] is not None
    assert created[0]["why_fit"]
    activity = client.get("/api/activity").json()
    assert any(event["action"] == "ai_search" for event in activity)

    calls = {"n": 0}

    def one_hit(db, query, limit=5):
        calls["n"] += 1
        return [{
            "company": "Only Clinic",
            "contact_name": "Asha",
            "email": "asha@onlyclinic.example",
            "website": "https://onlyclinic.example",
            "source_url": "https://onlyclinic.example/team",
            "snippet": "Only Clinic uses radios. asha@onlyclinic.example",
            "search_provider": "mock",
            "city": "Ahmedabad",
            "state": "Gujarat",
            "country": "India",
        }]

    monkeypatch.setattr("app.ai_search.runner.search_query", one_hit)
    thin = client.post("/api/search/ai", json={"text": "a single clinic in Gujarat", "rounds": 2})
    assert thin.status_code == 200
    assert thin.json()["rounds"] == 2
    assert calls["n"] >= 2
    assert any("official site" in query for query in thin.json()["plan"]["queries"])

    client.put("/api/providers/access", json={
        "provider": "ai_search",
        "role": "super_admin",
        "enabled": True,
        "daily_quota": 1,
        "monthly_quota": 1,
    })
    blocked = client.post("/api/search/ai", json={"text": "one more hospital search"})
    assert blocked.status_code == 429


def test_business_profile_is_used_in_the_outreach_draft(client):
    _admin(client)
    saved = client.put("/api/settings", json={
        "seller_name": "Boondock",
        "offering": "We sell Boondock Echo radios.",
        "ideal_customer": "Hospitals",
    })
    assert saved.status_code == 200
    assert saved.json()["offering"].startswith("We sell Boondock")
    lead = client.post("/api/leads", json={
        "company": "City Hospital",
        "website": "https://cityhospital.example",
        "industry": "healthcare",
        "contact_name": "Dr Patel",
    })
    run = client.post("/api/agents/run", json={"lead_id": lead.json()["id"]})
    assert run.status_code == 200
    assert "Boondock Echo" in run.json()["outreach"]["body"]


def test_bot_token_auth_leads_and_webhook(client, monkeypatch):
    _admin(client)
    monkeypatch.setenv("GROKBOT_WEBHOOK_URL", "https://bot.example/hook")
    monkeypatch.setenv("GROKBOT_WEBHOOK_SECRET", "sekret")
    get_settings.cache_clear()
    captured = {}

    class FakeResponse:
        status_code = 202

        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, *args, **kwargs):
            captured["timeout"] = kwargs.get("timeout")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr("app.bot.webhook.httpx.Client", FakeClient)

    created = client.post("/api/settings/bot-tokens", json={"name": "Grok production"})
    assert created.status_code == 200
    raw = created.json()["token"]
    assert raw.startswith("lpb_")
    listing = client.get("/api/settings/bot-tokens")
    assert raw not in listing.text
    assert client.get("/api/bot/requests").status_code == 401
    assert client.get("/api/bot/requests", headers={"Authorization": "Bearer wrong-token"}).status_code == 401

    deep = client.post("/api/search/deep", json={"text": "hospitals in Gujarat that might buy Boondock Echo"})
    assert deep.status_code == 200
    request_id = deep.json()["id"]
    assert deep.json()["status"] == "pending"
    assert deep.json()["webhook_status"] == "sent"
    assert captured["url"] == "https://bot.example/hook"
    assert captured["json"]["request_id"] == request_id
    assert captured["json"]["callback_base_url"] == "http://localhost:8000"
    assert "queries" in captured["json"]["plan"]
    assert captured["headers"]["X-LeadPilot-Webhook-Secret"] == "sekret"
    assert "sekret" not in deep.text

    headers = {"Authorization": f"Bearer {raw}"}
    pending = client.get("/api/bot/requests?status=pending", headers=headers)
    assert pending.status_code == 200
    assert any(item["id"] == request_id for item in pending.json())
    claim = client.post(f"/api/bot/requests/{request_id}/claim", headers=headers)
    assert claim.status_code == 200
    assert claim.json()["status"] == "claimed"
    done = client.post(f"/api/bot/requests/{request_id}/complete", headers=headers, json={"notes": "Checked public directories"})
    assert done.json()["status"] == "completed"
    assert "directories" in done.json()["notes"]

    payload = {
        "request_id": request_id,
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
                "why_fit": "Uses handheld radios and is expanding wards.",
                "source_url": "https://echobuyer.example/about",
            },
            {"company": "x"},
        ],
    }
    added = client.post("/api/bot/leads", headers=headers, json=payload)
    assert added.status_code == 200
    assert added.json()["created"] == 1
    assert added.json()["skipped"] == 1
    again = client.post("/api/bot/leads", headers=headers, json=payload)
    assert again.json()["duplicates"] == 1
    saved = next(lead for lead in client.get("/api/leads").json() if lead["company"] == "Echo Buyer Hospital")
    assert saved["source"] == "grokbot"
    assert saved["deep_search_request_id"] == request_id
    assert saved["score"] is not None
    assert saved["why_fit"].startswith("Uses handheld")
    counts = client.get("/api/search/ai").json()["sources"]
    assert counts["grokbot"] >= 1
    assert counts["app"] >= 0

    revoked = client.delete(f"/api/settings/bot-tokens/{created.json()['id']}")
    assert revoked.status_code == 200
    assert client.get("/api/bot/requests", headers=headers).status_code == 401
    get_settings.cache_clear()


def test_webhook_failure_still_queues_the_request(client, monkeypatch):
    _admin(client)
    monkeypatch.setenv("GROKBOT_WEBHOOK_URL", "https://bot.example/hook")
    get_settings.cache_clear()

    class Broken:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr("app.bot.webhook.httpx.Client", Broken)
    deep = client.post("/api/search/deep", json={"text": "clinics that need radios"})
    assert deep.status_code == 200
    assert deep.json()["status"] == "pending"
    assert deep.json()["webhook_status"] == "failed"
    get_settings.cache_clear()
