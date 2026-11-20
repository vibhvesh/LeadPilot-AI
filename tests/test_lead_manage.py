"""Assign, status, close, and the lead activity log."""

from app.core.database import SessionLocal
from app.models import Lead
from tests.helpers import login


def _admin(client):
    assert login(client, "vibhvesh@gmail.com", "Vibhvesh").status_code == 200


def _member(client):
    login(client, "pilot@example.com", "Pilot")
    _admin(client)
    users = client.get("/api/users").json()["users"]
    person = next(user for user in users if user["email"] == "pilot@example.com")
    assert client.post(f"/api/users/{person['id']}/decision", json={"decision": "approve"}).status_code == 200
    client.post("/auth/logout")
    assert login(client, "pilot@example.com", "Pilot").status_code == 200
    return person["id"]


def test_assign_claim_my_leads_and_bulk(client):
    member_id = _member(client)
    _admin(client)
    lead_id = client.post("/api/leads", json={"company": "Assign Co", "website": "https://assign.example", "contact_type": "linkedin_dm"}).json()["id"]
    assert client.get("/api/leads", params={"contact_type": "linkedin_dm"}).json()[0]["id"] == lead_id
    tagged = client.post("/api/leads", json={"company": "Tag Co", "website": "https://tag.example", "tags": ["linkedin_dm"]}).json()
    assert tagged["contact_type"] == "linkedin_dm"
    client.post("/auth/logout")
    assert login(client, "pilot@example.com", "Pilot").status_code == 200
    blocked = client.post(f"/api/leads/{lead_id}/assign", json={"user_id": member_id})
    assert blocked.status_code == 403
    db = SessionLocal()
    try:
        row = db.get(Lead, lead_id)
        row.owner_id = None
        db.commit()
    finally:
        db.close()
    claimed = client.post(f"/api/leads/{lead_id}/assign", json={"user_id": member_id})
    assert claimed.status_code == 200
    mine = client.get("/api/leads", params={"mine": True}).json()
    assert any(row["id"] == lead_id for row in mine)
    _admin(client)
    bulk = client.post("/api/leads/bulk-assign", json={"ids": [lead_id], "owner_id": member_id})
    assert bulk.status_code == 200


def test_status_close_reopen_and_activity(client):
    _admin(client)
    lead = client.post("/api/leads", json={"company": "Close Co", "website": "https://close.example"}).json()
    moved = client.patch(f"/api/leads/{lead['id']}", json={"status": "Replied"})
    assert moved.status_code == 200
    assert moved.json()["status"] == "Replied"
    missing = client.post(f"/api/leads/{lead['id']}/close", json={"outcome": "won", "reason": "no"})
    assert missing.status_code == 400
    closed = client.post(f"/api/leads/{lead['id']}/close", json={"outcome": "lost", "reason": "No budget this quarter"})
    assert closed.status_code == 200
    assert closed.json()["closed"] is True
    assert all(row["id"] != lead["id"] for row in client.get("/api/leads").json())
    shown = client.get("/api/leads", params={"show_closed": True}).json()
    assert any(row["id"] == lead["id"] for row in shown)
    reopened = client.post(f"/api/leads/{lead['id']}/reopen")
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "Contacted"
    second = client.post("/api/leads", json={"company": "Bulk Co", "website": "https://bulk.example"}).json()
    bulk = client.post("/api/leads/bulk-status", json={"ids": [lead["id"], second["id"]], "status": "Proposal"})
    assert bulk.status_code == 200
    events = client.get(f"/api/leads/{lead['id']}/activity").json()["events"]
    text = " ".join(event["summary"] for event in events)
    assert "Replied" in text
    assert "closed" in text.lower()
    assert "reopened" in text.lower()
