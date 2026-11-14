"""Industry Pulse cards, bot ingest, and read-only news fetch."""

from sqlalchemy import create_engine, delete, inspect, select, text

from app.core.database import Base, SessionLocal
from app.core.seed import ensure_role_permissions
from app.models import RolePermission
from app.pulse.classify import classify_urgency, normalize_urgency
from app.pulse.links import resolve_source_type
from app.pulse.schema import upgrade
from tests.helpers import login


def _admin(client):
    response = login(client, "vibhvesh@gmail.com", "Vibhvesh")
    assert response.status_code == 200


def _token(client) -> str:
    created = client.post("/api/settings/bot-tokens", json={"name": "Pulse bot"})
    assert created.status_code == 200
    return created.json()["token"]


def _sample_items():
    return [
        {
            "headline": "USCIS fee rule for H-1B petitions takes effect Monday",
            "why_it_matters": "Vendor-placed H-1B consultants may cost more to start, which changes which C2C reqs are worth submitting this week.",
            "urgency": "urgent",
            "source_type": "news",
            "url": "https://news.example/uscis-h1b-fee-rule",
            "links": [
                "https://news.example/uscis-h1b-fee-rule",
                {"url": "https://news.example/uscis-h1b-fee-rule-analysis"},
            ],
            "published_at": "2026-11-13",
            "topic": "H-1B policy",
        },
        {
            "headline": "Bill rates for US IT contractors are slipping this month",
            "url": "https://www.reddit.com/r/recruiting/comments/rates1/bill_rates",
            "published_at": "2026-11-01",
            "topic": "Bill rates",
        },
        {
            "headline": "Recap of a staffing conference in Dallas",
            "url": "https://www.linkedin.com/posts/staffing-weekly_dallas-recap",
            "published_at": "2026-10-02",
            "urgency": "fyi",
            "source_type": "social",
            "topic": "Conference",
        },
    ]


def test_urgency_and_source_type():
    assert classify_urgency("USCIS fee rule for H-1B petitions takes effect Monday") == "urgent"
    assert classify_urgency("Bill rates for US IT contractors are slipping this month") == "week"
    assert classify_urgency("Recap of a staffing conference in Dallas") == "fyi"
    assert normalize_urgency("this_week") == "week"
    assert resolve_source_type(None, "https://www.reddit.com/r/recruiting/comments/rates1/bill_rates") == "forum"
    assert resolve_source_type(None, "https://www.linkedin.com/posts/staffing-weekly_dallas-recap") == "social"
    assert resolve_source_type("news", "https://www.reddit.com/r/recruiting/comments/1/x") == "news"


def test_upgrade_creates_pulse_tables(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    import app.models  # noqa: F401

    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS pulse_comments"))
        connection.execute(text("DROP TABLE IF EXISTS pulse_items"))
    created = upgrade(engine)
    assert created == ["pulse_comments", "pulse_items"]
    assert upgrade(engine) == []
    columns = {column["name"] for column in inspect(engine).get_columns("pulse_items")}
    assert {"headline", "urgency", "source_type", "source_url", "links", "status"} <= columns


def test_bot_pulse_sorts_urgent_first_and_keeps_preferences(client):
    _admin(client)
    headers = {"Authorization": f"Bearer {_token(client)}"}
    assert client.post("/api/bot/pulse", json={"items": _sample_items()}).status_code == 401
    created = client.post("/api/bot/pulse", headers=headers, json={"items": _sample_items()})
    assert created.status_code == 200
    body = created.json()
    assert body["created"] == 3
    urgent = next(item for item in body["items"] if item["urgency"] == "urgent")
    week = next(item for item in body["items"] if item["topic"] == "Bill rates")
    fyi = next(item for item in body["items"] if item["urgency"] == "fyi")
    assert urgent["urgency_label"] == "Urgent"
    assert urgent["why_it_matters"].startswith("Vendor-placed")
    assert urgent["links"] == [
        "https://news.example/uscis-h1b-fee-rule",
        "https://news.example/uscis-h1b-fee-rule-analysis",
    ]
    assert week["urgency"] == "week"
    assert week["urgency_label"] == "This week"
    assert week["source_type"] == "forum"
    assert week["source_label"] == "Forum"
    assert "Bill rates" in week["why_it_matters"] or "this week" in week["why_it_matters"].lower()
    assert fyi["source_type"] == "social"
    assert fyi["url"].startswith("https://linkedin.com/")

    feed = client.get("/api/pulse?status=all").json()
    assert [item["urgency"] for item in feed["items"]] == ["urgent", "week", "fyi"]
    assert len(client.get("/api/pulse?urgency=urgent&status=all").json()["items"]) == 1
    assert len(client.get("/api/pulse?source_type=forum&status=all").json()["items"]) == 1
    assert len(client.get("/api/pulse?date_from=2026-11-10&date_to=2026-11-13&status=all").json()["items"]) == 1
    assert client.get("/api/pulse?urgency=nope").status_code == 400

    read = client.patch(f"/api/pulse/{urgent['id']}", json={"status": "read"})
    assert read.json()["status"] == "read"
    noted = client.post(f"/api/pulse/{urgent['id']}/comments", json={"body": "Track the fee rule"})
    assert noted.json()["comments"][0]["body"] == "Track the fee rule"
    client.patch(f"/api/pulse/{fyi['id']}", json={"status": "dismissed"})
    open_ids = {item["id"] for item in client.get("/api/pulse").json()["items"]}
    assert urgent["id"] not in open_ids
    assert fyi["id"] not in open_ids
    assert week["id"] in open_ids

    resent = client.post("/api/bot/pulse", headers=headers, json={
        "headline": "USCIS fee rule for H-1B petitions takes effect Monday",
        "url": "https://news.example/uscis-h1b-fee-rule?utm_source=bot",
        "why_it_matters": "Still the fee rule. Confirm which reqs to pause.",
    })
    assert resent.json()["updated"] == 1
    assert resent.json()["created"] == 0
    assert resent.json()["items"][0]["status"] == "read"
    assert resent.json()["items"][0]["url"] == "https://news.example/uscis-h1b-fee-rule"
    assert resent.json()["items"][0]["comments"][0]["body"] == "Track the fee rule"

    learned = client.get("/api/bot/pulse", headers=headers).json()
    learned_urgent = next(item for item in learned["items"] if item["id"] == urgent["id"])
    assert learned_urgent["status"] == "read"
    assert any(item["status"] == "dismissed" for item in learned["items"])
    noisy = client.post("/api/bot/pulse", headers=headers, json={"items": [
        {"headline": "A real forum thread about vendor management", "url": "https://news.ycombinator.com/item?id=1"},
        {"headline": "no link"},
        "nope",
    ]})
    assert noisy.json()["created"] == 1
    assert noisy.json()["skipped"] == 2


def test_manual_pulse_permissions_and_page(client):
    _admin(client)
    saved = client.post("/api/pulse", json={
        "headline": "Vendor management systems are tightening onboarding",
        "url": "https://www.example.com/vms-onboarding?utm_medium=email",
        "topic": "Vendor management",
        "links": "https://www.example.com/vms-onboarding-notes",
    })
    assert saved.status_code == 200
    item = saved.json()
    assert item["url"] == "https://example.com/vms-onboarding"
    assert "https://example.com/vms-onboarding-notes" in item["links"]
    assert item["urgency"] == "week"
    assert item["source_type"] == "news"
    blocked = client.post("/api/pulse", json={"headline": "Sign in to read this", "url": "https://www.linkedin.com/login"})
    assert blocked.status_code == 400
    assert "does not sign in" in blocked.json()["detail"]

    login(client, "pulse.member@example.com", "Pulse Member")
    _admin(client)
    users = client.get("/api/users").json()["users"]
    member = next(user for user in users if user["email"] == "pulse.member@example.com")
    client.post(f"/api/users/{member['id']}/decision", json={"decision": "approve"})
    client.put(f"/api/users/{member['id']}/permissions", json={"permissions": {"pulse": {"view": True, "manage": False}}})
    client.post("/auth/logout")
    login(client, "pulse.member@example.com", "Pulse Member")
    assert client.get("/api/pulse").status_code == 200
    assert client.patch(f"/api/pulse/{item['id']}", json={"status": "read"}).status_code == 403

    client.post("/auth/logout")
    _admin(client)
    page = client.get("/")
    assert 'data-tab="pulse"' in page.text
    assert "Industry Pulse" in page.text
    assert "never posts or signs in" in page.text
    assert client.get("/pulse").status_code == 200
    assert "Mark read" in client.get("/static/pulse-ui.js").text
    client.post("/auth/logout")
    assert client.get("/pulse", follow_redirects=False).status_code == 302


def test_pulse_fetch_reads_public_stories(client, monkeypatch):
    _admin(client)
    missing = client.post("/api/pulse/fetch", json={})
    assert missing.status_code == 400
    assert "search key" in missing.json()["detail"].lower() or "Tavily" in missing.json()["detail"]
    assert client.get("/api/pulse").json()["sources"] == {"web_search": False}

    def fake_documents(db, query, limit):
        assert "staffing" in query.lower() or "H-1B" in query or "H1B" in query
        return "tavily", [
            {"title": "Sign in", "url": "https://www.linkedin.com/login", "snippet": "Login wall"},
            {"title": "USCIS fee rule for H-1B petitions takes effect Monday", "url": "https://news.example/fee", "snippet": "The fee rule takes effect Monday."},
            {"title": "Hiring demand cools in US IT staffing this month", "url": "https://trade.example/demand", "snippet": "Staffing industry demand is softer."},
        ]

    monkeypatch.setattr("app.pulse.fetch.search_configured", lambda db: True)
    monkeypatch.setattr("app.pulse.fetch.search_documents", fake_documents)
    pulled = client.post("/api/pulse/fetch", json={})
    assert pulled.status_code == 200
    assert pulled.json()["provider"] == "tavily"
    assert pulled.json()["created"] == 2
    assert "Nothing was posted" in pulled.json()["note"]
    urls = {item["url"] for item in pulled.json()["items"]}
    assert "https://news.example/fee" in urls
    assert all("login" not in url for url in urls)
    urgent = next(item for item in pulled.json()["items"] if "fee" in item["url"])
    assert urgent["urgency"] == "urgent"
    assert urgent["source_type"] == "news"


def test_existing_roles_gain_pulse_access(client):
    _admin(client)
    db = SessionLocal()
    try:
        db.execute(delete(RolePermission).where(RolePermission.module == "pulse"))
        db.commit()
        ensure_role_permissions(db)
        db.commit()
        member = db.scalar(select(RolePermission).where(RolePermission.role == "member", RolePermission.module == "pulse"))
        admin = db.scalar(select(RolePermission).where(RolePermission.role == "admin", RolePermission.module == "pulse"))
        assert member is not None and member.can_view and member.can_manage
        assert admin is not None and admin.can_view and admin.can_manage
    finally:
        db.close()
