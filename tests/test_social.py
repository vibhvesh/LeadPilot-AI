"""Social feed: bot ingest, buckets, preferences, and read-only public fetch."""

from pathlib import Path

from sqlalchemy import create_engine, delete, inspect, select, text

from app.core.database import Base, SessionLocal
from app.core.seed import ensure_role_permissions
from app.models import RolePermission
from app.social.classify import classify_bucket, draft_reply, normalize_bucket
from app.social.links import canonical_url, is_fetchable_public_url, is_linkedin_public_post
from app.social.schema import upgrade
from app.social.x_api import parse_tweets, search_recent
from tests.helpers import login


def _admin(client):
    response = login(client, "vibhvesh@gmail.com", "Vibhvesh")
    assert response.status_code == 200
    return response


def _token(client) -> str:
    created = client.post("/api/settings/bot-tokens", json={"name": "Social bot"})
    assert created.status_code == 200
    return created.json()["token"]


def _sample_items():
    return [
        {
            "platform": "x",
            "url": "https://x.com/alexrivera/status/1234567890",
            "poster_name": "Alex Rivera",
            "poster_role": "Talent acquisition lead",
            "posted_at": "2026-11-13T15:04:00Z",
            "snippet": "Looking for C2C vendors who can staff US-based Java roles. H1B ok.",
            "topic": "C2C Java",
            "company": "Northwind Systems",
            "discussion_key": "northwind-c2c-java",
            "bucket": "reply",
            "why_it_matters": "Direct ask for C2C vendor partners on a US IT role.",
            "suggested_reply": "Hi Alex — we staff US-based Java engineers on C2C and can share three profiles today.",
            "work_auth": "C2C, H1B",
        },
        {
            "platform": "reddit",
            "url": "https://www.reddit.com/r/recruiting/comments/abc123/vendor_friendly_devops/",
            "poster_name": "hiringmgr",
            "posted_at": "2026-11-01T12:00:00Z",
            "snippet": "Our SI is hiring a DevOps contractor. Curious what others pay for W2 vs C2C.",
            "topic": "DevOps rates",
            "company": "Fabrikam",
            "discussion_key": "fabrikam-devops-rates",
            "bucket": "engage",
        },
        {
            "platform": "linkedin",
            "url": "https://www.linkedin.com/posts/casey-lee_activity-987",
            "posted_at": "2026-10-02T12:00:00Z",
            "snippet": "Photos from the Austin IT leadership breakfast.",
            "topic": "Austin breakfast",
            "bucket": "fyi",
        },
    ]


def test_classify_reply_engage_and_fyi():
    assert classify_bucket("Looking for C2C vendors for a Java role in Texas") == "reply"
    assert classify_bucket("Open to vendors for a US-based DevOps contract") == "reply"
    assert classify_bucket("Anyone know recruiters for a W2 data role?") == "reply"
    assert classify_bucket("Our H1B transfer process is slow this quarter") == "engage"
    assert classify_bucket("We are hiring a Java developer") == "engage"
    assert classify_bucket("Photos from the Austin meetup") == "fyi"
    assert normalize_bucket("reply_to") == "reply"
    assert normalize_bucket("FYI") == "fyi"
    assert classify_bucket("") == "fyi"
    assert draft_reply("fyi", poster_name="Alex", company="Northwind", work_auth="C2C") == ""
    reply = draft_reply("reply", poster_name="Alex", company="Northwind", work_auth="C2C")
    assert "Alex" in reply and "Northwind" in reply and "C2C" in reply


def test_public_links_reject_login_walls_and_keep_post_urls():
    assert canonical_url("https://www.X.com/Alex/status/5?utm_source=share") == "https://x.com/Alex/status/5"
    assert is_linkedin_public_post("https://www.linkedin.com/posts/casey_activity-55")
    assert not is_linkedin_public_post("https://www.linkedin.com/in/casey")
    assert is_fetchable_public_url("https://linkedin.com/posts/casey_activity-55")
    assert not is_fetchable_public_url("https://example.com/blog")
    try:
        canonical_url("https://www.linkedin.com/login")
    except Exception as exc:
        assert "does not sign in" in str(exc)
    else:
        raise AssertionError("a LinkedIn login URL should be rejected")
    try:
        canonical_url("javascript:alert(1)")
    except Exception as exc:
        assert "public" in str(exc).lower()
    else:
        raise AssertionError("a javascript URL should be rejected")


def test_x_api_only_reads_public_posts(monkeypatch):
    source = Path("app/social/x_api.py").read_text()
    assert "client.get" in source
    assert ".post(" not in source
    calls = []

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "data": [
                    {
                        "id": "99",
                        "author_id": "7",
                        "conversation_id": "50",
                        "text": "Looking for C2C vendors",
                        "created_at": "2026-11-13T15:04:00.000Z",
                    }
                ],
                "includes": {"users": [{"id": "7", "name": "Alex Rivera", "username": "alexrivera", "description": "Talent lead"}]},
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, headers=None, params=None):
            calls.append(("GET", url))
            return FakeResponse()

        def post(self, *args, **kwargs):
            raise AssertionError("X fetch must not POST")

    monkeypatch.setattr("app.social.x_api.httpx.Client", FakeClient)
    rows = search_recent("test-token", "C2C", 5)
    assert calls and calls[0][0] == "GET"
    assert calls[0][1].endswith("/tweets/search/recent")
    assert rows[0]["url"] == "https://x.com/alexrivera/status/99"
    assert rows[0]["discussion_key"] == "50"
    assert rows[0]["poster_name"] == "Alex Rivera"
    single = parse_tweets({"data": {"id": "1", "text": "Hi"}, "includes": {"users": []}})
    assert single == []


def test_upgrade_creates_social_tables_and_adds_columns(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    import app.models  # noqa: F401

    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS social_comments"))
        connection.execute(text("DROP TABLE IF EXISTS social_items"))
    created = upgrade(engine)
    assert created == ["social_comments", "social_items"]
    names = set(inspect(engine).get_table_names())
    assert {"social_items", "social_comments"} <= names
    assert upgrade(engine) == []

    altered = create_engine(f"sqlite:///{tmp_path / 'partial.db'}")
    with altered.begin() as connection:
        connection.execute(text("CREATE TABLE social_items (id INTEGER PRIMARY KEY)"))
    upgrade(altered)
    columns = {column["name"] for column in inspect(altered).get_columns("social_items")}
    assert {"post_url", "url_hash", "bucket", "status", "company", "suggested_reply"} <= columns


def test_bot_ingest_groups_filters_and_keeps_preferences(client):
    _admin(client)
    raw = _token(client)
    headers = {"Authorization": f"Bearer {raw}"}
    assert client.post("/api/bot/social", json={"items": _sample_items()}).status_code == 401
    created = client.post("/api/bot/social", headers=headers, json={"items": _sample_items()})
    assert created.status_code == 200
    body = created.json()
    assert body["created"] == 3
    assert body["skipped"] == 0
    by_company = {item["company"]: item for item in body["items"]}
    reply = by_company["Northwind Systems"]
    assert reply["bucket"] == "reply"
    assert reply["bucket_label"] == "Reply to"
    assert reply["suggested_reply"].startswith("Hi Alex")
    assert reply["work_auth"] == "C2C, H1B"
    assert reply["why_it_matters"].startswith("Direct ask")
    assert "lead_id" not in reply
    engage = by_company["Fabrikam"]
    assert engage["bucket"] == "engage"
    assert engage["url"] == "https://reddit.com/r/recruiting/comments/abc123/vendor_friendly_devops"
    assert "Fabrikam" in engage["suggested_reply"]
    fyi = next(item for item in body["items"] if item["bucket"] == "fyi")
    assert fyi["suggested_reply"] == ""
    assert fyi["platform"] == "linkedin"

    follow = client.post("/api/bot/social", headers=headers, json={
        "url": "https://x.com/alexrivera/status/1234567891",
        "snippet": "Still looking for those C2C vendors.",
        "company": "Northwind Systems",
        "topic": "C2C Java",
        "discussion_key": "northwind-c2c-java",
        "posted_at": "2026-11-13T18:00:00Z",
    })
    assert follow.status_code == 200
    assert follow.json()["created"] == 1

    feed = client.get("/api/social?status=all").json()
    group = next(item for item in feed["groups"] if item["discussion_key"] == "northwind-c2c-java")
    assert len(group["item_ids"]) == 2
    assert group["company"] == "Northwind Systems"
    november = client.get("/api/social?date_from=2026-11-10&date_to=2026-11-13&status=all").json()
    assert {item["company"] for item in november["items"]} == {"Northwind Systems"}
    assert len(client.get("/api/social?platform=reddit&status=all").json()["items"]) == 1
    assert len(client.get("/api/social?company=fabrikam&status=all").json()["items"]) == 1
    assert len(client.get("/api/social?topic=C2C&bucket=reply_to&status=all").json()["items"]) == 2
    assert client.get("/api/social?platform=myspace").status_code == 400
    assert client.get("/api/social?date_from=13-11-2026").status_code == 400

    done = client.patch(f"/api/social/{reply['id']}", json={"status": "done"})
    assert done.status_code == 200
    noted = client.post(f"/api/social/{reply['id']}/comments", json={"body": "Skip bench-only posts"})
    assert noted.json()["comments"][0]["body"] == "Skip bench-only posts"
    assert noted.json()["status"] == "done"
    ignored = client.patch(f"/api/social/{fyi['id']}", json={"status": "ignored"})
    assert ignored.json()["status"] == "ignored"
    open_feed = client.get("/api/social").json()
    open_ids = {item["id"] for item in open_feed["items"]}
    assert reply["id"] not in open_ids
    assert fyi["id"] not in open_ids
    assert engage["id"] in open_ids

    resent = client.post("/api/bot/social", headers=headers, json={
        "url": "https://x.com/alexrivera/status/1234567890",
        "snippet": "Still looking for C2C vendors next week.",
        "company": "Northwind Systems",
    })
    assert resent.json()["updated"] == 1
    assert resent.json()["created"] == 0
    assert resent.json()["items"][0]["status"] == "done"
    assert "next week" in resent.json()["items"][0]["snippet"]
    assert resent.json()["items"][0]["comments"][0]["body"] == "Skip bench-only posts"

    learned = client.get("/api/bot/social", headers=headers).json()
    learned_reply = next(item for item in learned["items"] if item["id"] == reply["id"])
    assert learned_reply["status"] == "done"
    assert learned_reply["comments"][0]["body"] == "Skip bench-only posts"
    assert any(item["status"] == "ignored" for item in learned["items"])

    noisy = client.post("/api/bot/social", headers=headers, json={"items": [
        {"url": "https://reddit.com/r/recruiting/comments/zzz/new"},
        {"url": "javascript:alert(1)"},
        "not-an-item",
    ]})
    assert noisy.json()["created"] == 1
    assert noisy.json()["skipped"] == 2
    assert client.post("/api/bot/social", headers=headers, json={"items": []}).status_code == 400
    assert client.post("/api/bot/leads", headers=headers, json={"request_id": 99999, "leads": [{"company": "Acme Corp"}]}).status_code == 404


def test_manual_link_permissions_and_page(client):
    _admin(client)
    saved = client.post("/api/social", json={
        "url": "https://www.linkedin.com/posts/casey_activity-55?utm_source=share",
        "poster_name": "Casey Lee",
        "snippet": "Looking for C2C vendors for a US data role.",
        "company": "Contoso",
        "topic": "C2C data",
    })
    assert saved.status_code == 200
    item = saved.json()
    assert item["url"] == "https://linkedin.com/posts/casey_activity-55"
    assert item["platform"] == "linkedin"
    assert item["bucket"] == "reply"
    assert "Casey Lee" in item["suggested_reply"]
    assert "Contoso" in item["suggested_reply"]
    blocked = client.post("/api/social", json={"url": "https://www.linkedin.com/login", "snippet": "Sign in"})
    assert blocked.status_code == 400
    assert "does not sign in" in blocked.json()["detail"]
    assert client.post(f"/api/social/{item['id']}/comments", json={"body": "  "}).status_code == 400

    lead = client.post("/api/leads", json={"company": "Contoso", "website": "https://contoso.example"}).json()
    assert "social_signals" not in lead
    assert "signals" not in lead

    login(client, "member@example.com", "Member")
    _admin(client)
    users = client.get("/api/users").json()["users"]
    member = next(user for user in users if user["email"] == "member@example.com")
    client.post(f"/api/users/{member['id']}/decision", json={"decision": "approve"})
    client.put(f"/api/users/{member['id']}/permissions", json={"permissions": {"social": {"view": True, "manage": False}}})
    client.post("/auth/logout")
    login(client, "member@example.com", "Member")
    assert client.get("/api/social").status_code == 200
    assert client.post("/api/social", json={"url": "https://reddit.com/r/test/comments/1/hi", "snippet": "Hello"}).status_code == 403
    assert client.patch(f"/api/social/{item['id']}", json={"status": "done"}).status_code == 403

    client.post("/auth/logout")
    _admin(client)
    client.put(f"/api/users/{member['id']}/permissions", json={"permissions": {"social": {"view": False, "manage": False}}})
    client.post("/auth/logout")
    login(client, "member@example.com", "Member")
    assert client.get("/api/social").status_code == 403

    client.post("/auth/logout")
    _admin(client)
    page = client.get("/")
    assert 'data-tab="social"' in page.text
    assert "LeadPilot never posts" in page.text
    assert 'src="/static/mascot.js"' in page.text
    assert client.get("/social").status_code == 200
    script = client.get("/static/social-ui.js").text
    assert "Copy reply" in script
    assert "/api/social" in script
    client.post("/auth/logout")
    assert client.get("/social", follow_redirects=False).status_code == 302


def test_public_fetch_reads_and_never_posts(client, monkeypatch):
    _admin(client)
    missing = client.post("/api/social/fetch", json={})
    assert missing.status_code == 400
    assert "API keys" in missing.json()["detail"]
    assert client.get("/api/social").json()["sources"] == {"x_api": False, "web_search": False}

    saved = client.put("/api/providers/keys", json={"provider": "x", "api_key": "x-test-key-123456"})
    assert saved.status_code == 200
    assert client.get("/api/social").json()["sources"]["x_api"] is True
    calls = {"search": 0, "documents": 0}

    def fake_search(token, query, limit):
        calls["search"] += 1
        assert token
        assert "C2C" in query
        return [{
            "platform": "x",
            "url": "https://x.com/alexrivera/status/77",
            "poster_name": "Alex Rivera",
            "snippet": "Looking for C2C vendors for a US Java role",
            "discussion_key": "77",
            "topic": "US IT vendor hiring",
            "posted_at": "2026-11-13T15:04:00Z",
        }]

    def fail_documents(*args, **kwargs):
        calls["documents"] += 1
        raise AssertionError("X API results should not fall through to web search")

    monkeypatch.setattr("app.social.fetch.search_recent", fake_search)
    monkeypatch.setattr("app.social.fetch.search_documents", fail_documents)
    pulled = client.post("/api/social/fetch", json={})
    assert pulled.status_code == 200
    assert pulled.json()["provider"] == "x"
    assert pulled.json()["created"] == 1
    assert "Nothing was posted" in pulled.json()["note"]
    assert calls == {"search": 1, "documents": 0}
    assert client.get("/api/social").json()["items"][0]["bucket"] == "reply"

    monkeypatch.setattr("app.social.fetch.x_configured", lambda db: False)
    monkeypatch.setattr("app.social.fetch.search_configured", lambda db: True)

    def fake_documents(db, query, limit):
        return "tavily", [
            {"title": "Login", "url": "https://www.linkedin.com/login", "snippet": "Sign in"},
            {"title": "Post", "url": "https://www.linkedin.com/posts/northwind_activity-1", "snippet": "Hiring a Java developer, C2C ok"},
            {"title": "Blog", "url": "https://example.com/blog", "snippet": "Not a social post"},
            {"title": "Reddit", "url": "https://www.reddit.com/r/recruiting/comments/abc/c2c", "snippet": "Open to vendors for contract devops"},
        ]

    monkeypatch.setattr("app.social.fetch.search_documents", fake_documents)
    web = client.post("/api/social/fetch", json={"query": "C2C vendors"})
    assert web.status_code == 200
    assert web.json()["provider"] == "tavily"
    urls = {item["url"] for item in web.json()["items"]}
    assert "https://linkedin.com/posts/northwind_activity-1" in urls
    assert "https://reddit.com/r/recruiting/comments/abc/c2c" in urls
    assert all("login" not in url for url in urls)
    assert all("example.com" not in url for url in urls)


def test_existing_roles_gain_the_social_module(client):
    _admin(client)
    db = SessionLocal()
    try:
        db.execute(delete(RolePermission).where(RolePermission.module == "social"))
        db.commit()
        ensure_role_permissions(db)
        db.commit()
        member = db.scalar(select(RolePermission).where(RolePermission.role == "member", RolePermission.module == "social"))
        admin = db.scalar(select(RolePermission).where(RolePermission.role == "admin", RolePermission.module == "social"))
        assert member is not None and member.can_view and member.can_manage
        assert admin is not None and admin.can_view and admin.can_manage
    finally:
        db.close()
