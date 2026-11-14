"""Outreach sequence, team visibility, and peer coverage."""

from datetime import timedelta

from app.core.database import SessionLocal
from app.models import FollowUp, Lead, User
from app.models.identity import utcnow
from tests.helpers import login


def _admin(client):
    assert login(client, "vibhvesh@gmail.com", "Vibhvesh").status_code == 200


def test_templates_seed_and_merge(client):
    _admin(client)
    created = client.post("/api/leads", json={"company": "Orbit Staffing", "contact_name": "Nagam Srinivas", "email": "nagam@orbit.example"})
    assert created.status_code == 200
    lead_id = created.json()["id"]
    preview = client.get(f"/api/leads/{lead_id}/outreach?template_key=first")
    assert preview.status_code == 200
    body = preview.json()
    assert "Nagam" in body["body"]
    assert "Orbit Staffing" in body["body"]
    assert body["blocked"] is None
    assert "mailto:" in body["mailto"]
    saved = client.put("/api/outreach/templates/first", json={"subject": "Hello {{first_name}}", "body": "From {{sender_name}} at {{company}}"})
    assert saved.status_code == 200
    again = client.get(f"/api/leads/{lead_id}/outreach?template_key=first").json()
    assert again["subject"].startswith("Hello Nagam")


def test_first_outreach_is_once_and_followup_is_scheduled(client):
    _admin(client)
    lead_id = client.post("/api/leads", json={"company": "Pad Systems", "contact_name": "Asha Rao", "email": "asha@pad.example"}).json()["id"]
    sent = client.post(f"/api/leads/{lead_id}/outreach/confirm", json={"template_key": "first", "subject": "Hello", "body": "Note", "followup_days": 7})
    assert sent.status_code == 200
    assert "reached out" in sent.json()["summary"]
    blocked = client.post(f"/api/leads/{lead_id}/outreach/confirm", json={"template_key": "first", "subject": "Again", "body": "No"})
    assert blocked.status_code == 409
    nxt = client.post(f"/api/leads/{lead_id}/outreach/confirm", json={"template_key": "followup_1", "subject": "Checking in", "body": "Still here"})
    assert nxt.status_code == 200
    activity = client.get(f"/api/leads/{lead_id}/activity").json()["events"]
    assert any("reached out to Asha Rao" in row["summary"] for row in activity)
    listed = client.get("/api/leads").json()
    row = next(item for item in listed if item["id"] == lead_id)
    assert row["contacted_badge"].startswith("Contacted by")
    dup = client.post("/api/leads", json={"company": "Other Pad", "email": "asha@pad.example"})
    assert dup.status_code == 409


def test_admin_override_and_peer_coverage(client):
    _admin(client)
    lead_id = client.post("/api/leads", json={"company": "Cover Co", "contact_name": "Lee", "email": "lee@cover.example"}).json()["id"]
    assert client.post(f"/api/leads/{lead_id}/outreach/confirm", json={"template_key": "first", "subject": "Hi", "body": "Hi"}).status_code == 200
    denied = client.post(f"/api/leads/{lead_id}/outreach/confirm", json={"template_key": "first", "subject": "Hi", "body": "Hi"})
    assert denied.status_code == 409
    allowed = client.post(
        f"/api/leads/{lead_id}/outreach/confirm",
        json={"template_key": "first", "subject": "Hi", "body": "Hi", "override_reason": "They asked for a fresh note"},
    )
    assert allowed.status_code == 200
    me = client.get("/api/me").json()
    assert client.put("/api/me/coverage", json={"on_leave": True, "cover_user_id": me["id"]}).status_code == 200
    db = SessionLocal()
    try:
        lead = db.get(Lead, lead_id)
        lead.owner_id = me["id"]
        follow = db.query(FollowUp).filter(FollowUp.lead_id == lead_id).first()
        follow.due_at = utcnow() - timedelta(hours=1)
        follow.user_id = me["id"]
        db.commit()
    finally:
        db.close()
    due = client.get("/api/outreach/due").json()["items"]
    assert any(item["lead_id"] == lead_id for item in due)
    assert client.post(f"/api/leads/{lead_id}/takeover").status_code == 200
    note = client.post(f"/api/leads/{lead_id}/note", json={"body": "Called the front desk"})
    assert note.status_code == 200
    assert any("added a note" in row["summary"] for row in note.json()["events"])
