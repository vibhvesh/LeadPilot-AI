"""Cockpit summary: real counts, and null sections the caller cannot view."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import DeepSearchRequest, Lead, SocialItem
from tests.helpers import login


def _admin(client):
    response = login(client, "vibhvesh@gmail.com", "Vibhvesh")
    assert response.status_code == 200
    return response


def _approve(client, email, name):
    login(client, email, name)
    _admin(client)
    users = client.get("/api/users").json()["users"]
    person = next(user for user in users if user["email"] == email)
    assert client.post(f"/api/users/{person['id']}/decision", json={"decision": "approve"}).status_code == 200
    return person


def test_summary_requires_sign_in(client):
    assert client.get("/api/dashboard/summary").status_code == 401


def test_summary_counts_real_rows_and_hides_nothing_from_an_admin(client):
    _admin(client)
    me = client.get("/api/me").json()
    created = []
    for body in (
        {"company": "Full Contact Co", "email": "ada@full.example", "phone": "+1-202-555-0142", "website": "https://full.example", "estimated_value": 80000},
        {"company": "Email Only Co", "email": "bea@email.example", "website": "https://email.example", "estimated_value": 20000},
        {"company": "Phone Only Co", "phone": "+1-202-555-0199", "website": "https://phone.example"},
        {"company": "Blank Co", "website": "https://blank.example", "estimated_value": 5000},
        {"company": "Old New Co", "email": "old@new.example", "website": "https://old.example"},
    ):
        saved = client.post("/api/leads", json=body)
        assert saved.status_code == 200
        created.append(saved.json())
    by_company = {row["company"]: row for row in created}
    assert client.patch(f"/api/leads/{by_company['Blank Co']['id']}", json={"status": "Won"}).status_code == 200
    assert client.patch(f"/api/leads/{by_company['Phone Only Co']['id']}", json={"status": "Contacted"}).status_code == 200

    past = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    overdue = client.post("/api/followups", json={"title": "Call Full Contact", "lead_id": by_company["Full Contact Co"]["id"], "due_at": past})
    assert overdue.status_code == 200
    assert client.post("/api/followups", json={"title": "Later note", "due_at": future}).status_code == 200
    done = client.post("/api/followups", json={"title": "Already done", "due_at": past})
    assert client.patch(f"/api/followups/{done.json()['id']}", json={"status": "done"}).status_code == 200

    reply = client.post("/api/social", json={"url": "https://example.com/cockpit-reply", "snippet": "Looking for a vendor", "bucket": "reply"})
    engage = client.post("/api/social", json={"url": "https://example.com/cockpit-engage", "snippet": "Rate discussion", "bucket": "engage"})
    closed = client.post("/api/social", json={"url": "https://example.com/cockpit-closed", "snippet": "Old ask", "bucket": "reply"})
    assert reply.status_code == engage.status_code == closed.status_code == 200
    assert client.patch(f"/api/social/{closed.json()['id']}", json={"status": "done"}).status_code == 200

    urgent = client.post("/api/pulse", json={"headline": "Fee rule Monday", "url": "https://example.com/cockpit-urgent", "urgency": "urgent"})
    fyi = client.post("/api/pulse", json={"headline": "Quiet note", "url": "https://example.com/cockpit-fyi", "urgency": "fyi"})
    dismissed = client.post("/api/pulse", json={"headline": "Old urgent", "url": "https://example.com/cockpit-old", "urgency": "urgent"})
    assert urgent.status_code == fyi.status_code == dismissed.status_code == 200
    assert client.patch(f"/api/pulse/{dismissed.json()['id']}", json={"status": "dismissed"}).status_code == 200

    ten_days = datetime.now(timezone.utc) - timedelta(days=10)
    two_days = datetime.now(timezone.utc) - timedelta(days=2)
    db = SessionLocal()
    try:
        scores = {"Full Contact Co": 90, "Email Only Co": 40, "Phone Only Co": 99, "Old New Co": 70}
        for company, score in scores.items():
            lead = db.scalars(select(Lead).where(Lead.company == company)).one()
            lead.score = score
        full = db.scalars(select(Lead).where(Lead.company == "Full Contact Co")).one()
        full.source = "grokbot"
        for company in ("Blank Co", "Old New Co"):
            lead = db.scalars(select(Lead).where(Lead.company == company)).one()
            lead.created_at = ten_days
        social = db.scalars(select(SocialItem).where(SocialItem.id == reply.json()["id"])).one()
        social.source = "bot"
        social.created_at = two_days
        db.add(DeepSearchRequest(user_id=me["id"], text="hospitals that need a vendor", plan={}, status="pending", webhook_status="failed"))
        db.add(DeepSearchRequest(user_id=me["id"], text="finished search", plan={}, status="completed", webhook_status="sent"))
        db.commit()
    finally:
        db.close()

    body = client.get("/api/dashboard/summary")
    assert body.status_code == 200
    data = body.json()
    assert data["refresh_seconds"] == 60
    assert data["role"] == "super_admin"
    leads = data["leads"]
    assert leads["total"] == 5
    assert leads["new_today"] == 3
    assert leads["new_this_week"] == 3
    assert leads["by_status"]["New"] == 3
    assert leads["by_status"]["Contacted"] == 1
    assert leads["by_status"]["Won"] == 1
    assert leads["by_status"]["Qualified"] == 0
    assert leads["by_status"]["Lost"] == 0
    assert leads["conversion_rate"] == 0.2
    assert leads["pipeline_value"] == 100000
    assert leads["contact"] == {"full": 1, "phone_only": 1, "email_only": 2, "missing": 1}
    assert [row["company"] for row in leads["top_uncontacted"][:3]] == ["Full Contact Co", "Old New Co", "Email Only Co"]
    assert all(row["status"] == "New" for row in leads["top_uncontacted"])
    assert leads["top_uncontacted"][0]["score"] == 90
    assert len(leads["trend"]["days"]) == 7
    assert leads["trend"]["previous_week"] == 2
    assert leads["trend"]["delta"] == leads["trend"]["this_week"] - leads["trend"]["previous_week"]
    assert leads["trend"]["this_week"] == 3
    assert data["followups"] == {"open": 2, "overdue": 1}
    assert data["social"]["reply"] == 1
    assert data["social"]["engage"] == 1
    assert len(data["social"]["newest_replies"]) == 1
    assert "vendor" in data["social"]["newest_replies"][0]["snippet"]
    assert data["pulse"]["urgent"] == 1
    assert data["pulse"]["urgent_items"][0]["headline"]
    assert data["bot"]["requests"]["pending"] == 1
    assert data["bot"]["requests"]["completed"] == 1
    assert data["bot"]["webhook_failed"] == 1
    assert data["bot"]["last_ingest_at"]
    assert data["bot"]["sources"]["leads"]
    assert data["bot"]["sources"]["social"]
    assert data["bot"]["sources"]["leads"] > data["bot"]["sources"]["social"]
    assert data["health"]["api"] == "ok"
    assert data["health"]["database"] == "ok"
    assert data["health"]["llm_present"] is False
    assert data["health"]["search_present"] is False
    assert data["health"]["keys"]
    assert all(set(row) == {"provider", "configured"} and row["configured"] is False for row in data["health"]["keys"])
    assert data["team"]["approved"] >= 1
    assert data["activity"]["activities_today"] >= 1
    assert data["activity"]["recent"]
    assert "detail" not in data["activity"]["recent"][0]
    assert data["approvals"]["pending"] == 0
    raw = body.text
    assert "ciphertext" not in raw
    assert "api_key" not in raw
    assert "sk-" not in raw


def test_summary_is_empty_without_invented_numbers(client):
    _admin(client)
    data = client.get("/api/dashboard/summary").json()
    assert data["leads"]["total"] == 0
    assert data["leads"]["new_today"] == 0
    assert data["leads"]["new_this_week"] == 0
    assert data["leads"]["conversion_rate"] == 0
    assert data["leads"]["top_uncontacted"] == []
    assert data["leads"]["contact"] == {"full": 0, "phone_only": 0, "email_only": 0, "missing": 0}
    assert data["leads"]["trend"]["delta"] == 0
    assert data["leads"]["trend"]["pitch"] == 0
    assert [day["count"] for day in data["leads"]["trend"]["days"]] == [0, 0, 0, 0, 0, 0, 0]
    assert data["followups"] == {"open": 0, "overdue": 0}
    assert data["social"]["reply"] == 0
    assert data["social"]["engage"] == 0
    assert data["social"]["newest_replies"] == []
    assert data["pulse"]["urgent"] == 0
    assert data["pulse"]["urgent_items"] == []
    assert data["bot"]["last_ingest_at"] is None
    assert data["bot"]["requests"] == {"pending": 0, "claimed": 0, "completed": 0, "other": 0}


def test_summary_hides_sections_the_role_cannot_view(client):
    _admin(client)
    client.post("/api/leads", json={"company": "Visible Co", "email": "vis@example.com", "website": "https://visible.example"})
    client.post("/api/followups", json={"title": "Hidden from dashboard-only", "due_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()})
    client.post("/api/social", json={"url": "https://example.com/hidden-reply", "snippet": "vendor?", "bucket": "reply"})
    client.post("/api/pulse", json={"headline": "Hidden urgent", "url": "https://example.com/hidden-urgent", "urgency": "urgent"})

    _approve(client, "pilot@example.com", "Pilot")
    client.post("/auth/logout")
    login(client, "pilot@example.com", "Pilot")
    member = client.get("/api/dashboard/summary").json()
    assert member["leads"]["total"] == 1
    assert member["followups"]["open"] == 1
    assert member["social"]["reply"] == 1
    assert member["pulse"]["urgent"] == 1
    assert member["bot"]["requests"]["pending"] == 0
    assert member["health"]["keys"] is None
    assert member["health"]["llm_present"] is False
    assert member["team"]["approved"] >= 1
    assert member["activity"] is None
    assert member["approvals"] is None
    assert "failed_today" not in str(member["team"])

    client.post("/auth/logout")
    _admin(client)
    users = client.get("/api/users").json()["users"]
    pilot = next(user for user in users if user["email"] == "pilot@example.com")
    override = {module: {"view": module == "dashboard", "manage": False} for module in client.get("/api/me").json()["permissions"]}
    assert client.put(f"/api/users/{pilot['id']}/permissions", json={"permissions": override}).status_code == 200
    client.post("/auth/logout")
    login(client, "pilot@example.com", "Pilot")
    locked = client.get("/api/dashboard/summary").json()
    assert locked["leads"]["total"] == 1
    assert locked["followups"] is None
    assert locked["social"] is None
    assert locked["pulse"] is None
    assert locked["bot"] is None
    assert locked["team"] is None
    assert locked["activity"] is None
    assert locked["approvals"] is None
    assert locked["health"]["keys"] is None
    assert locked["health"]["database"] == "ok"
    assert "Hidden from dashboard-only" not in client.get("/api/dashboard/summary").text
    assert "vis@example.com" not in client.get("/api/dashboard/summary").text


def test_homepage_serves_the_cockpit_modules(client):
    _admin(client)
    page = client.get("/")
    assert page.status_code == 200
    assert 'id="cockpit"' in page.text
    assert 'id="overview"' in page.text
    for name in (
        "cockpit/cockpit.css",
        "cockpit/widgets.js",
        "cockpit/cockpit.js",
        "cockpit/annunciator.js",
        "cockpit/leads.js",
        "cockpit/attitude.js",
        "cockpit/conversion.js",
        "cockpit/contact.js",
        "cockpit/pipeline.js",
        "cockpit/uncontacted.js",
        "cockpit/followups.js",
        "cockpit/social.js",
        "cockpit/pulse.js",
        "cockpit/bot.js",
        "cockpit/health.js",
        "cockpit/team.js",
    ):
        assert name in page.text
        asset = client.get("/static/" + name)
        assert asset.status_code == 200, name
    css = client.get("/static/cockpit/cockpit.css").text
    assert "prefers-reduced-motion" in css
    assert "@media (max-width: 640px)" in css
