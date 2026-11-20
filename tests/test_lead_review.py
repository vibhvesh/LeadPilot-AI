"""Close requests and transfers that wait for acceptance."""

from tests.helpers import login
from tests.test_lead_manage import _member


def _admin(client):
    assert login(client, "vibhvesh@gmail.com", "Vibhvesh").status_code == 200


def test_member_cannot_close_and_admin_approves_or_rejects(client):
    member_id = _member(client)
    lead = client.post("/api/leads", json={"company": "Review Co", "website": "https://review.example"}).json()
    denied = client.post(f"/api/leads/{lead['id']}/close", json={"outcome": "won", "reason": "We signed them"})
    assert denied.status_code == 403
    asked = client.post(f"/api/leads/{lead['id']}/request-close", json={"outcome": "won", "reason": "They signed the order"})
    assert asked.status_code == 200
    assert asked.json()["status"] == "In review"
    assert asked.json()["closed"] is False
    client.post("/auth/logout")
    _admin(client)
    waiting = client.get("/api/leads", params={"awaiting_review": True}).json()
    assert any(row["id"] == lead["id"] for row in waiting)
    assert client.get("/api/leads/queues").json()["awaiting_review"] >= 1
    rejected = client.post(f"/api/leads/{lead['id']}/review-close", json={"decision": "reject", "comment": "Need a signed note first"})
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "New"
    client.post("/auth/logout")
    login(client, "pilot@example.com", "Pilot")
    client.post(f"/api/leads/{lead['id']}/request-close", json={"outcome": "lost", "reason": "They chose another vendor"})
    client.post("/auth/logout")
    _admin(client)
    approved = client.post(f"/api/leads/{lead['id']}/review-close", json={"decision": "approve"})
    assert approved.status_code == 200
    assert approved.json()["status"] == "Lost"
    assert approved.json()["closed"] is True
    assert member_id


def test_transfer_waits_until_accepted_and_decline_returns_it(client):
    member_id = _member(client)
    _admin(client)
    me = client.get("/api/me").json()["id"]
    lead = client.post("/api/leads", json={"company": "Handoff Co", "website": "https://handoff.example"}).json()
    offered = client.post(f"/api/leads/{lead['id']}/assign", json={"user_id": member_id})
    assert offered.status_code == 200
    assert offered.json()["owner_id"] == me
    assert offered.json()["pending_owner_id"] == member_id
    client.post("/auth/logout")
    login(client, "pilot@example.com", "Pilot")
    pending = client.get("/api/leads", params={"pending_for_me": True}).json()
    assert any(row["id"] == lead["id"] for row in pending)
    declined = client.post(f"/api/leads/{lead['id']}/decline", json={"reason": "I am at capacity"})
    assert declined.status_code == 200
    assert declined.json()["owner_id"] == me
    assert declined.json()["pending_owner_id"] is None
    client.post("/auth/logout")
    _admin(client)
    client.post(f"/api/leads/{lead['id']}/assign", json={"user_id": member_id})
    client.post("/auth/logout")
    login(client, "pilot@example.com", "Pilot")
    accepted = client.post(f"/api/leads/{lead['id']}/accept")
    assert accepted.status_code == 200
    assert accepted.json()["owner_id"] == member_id
    assert accepted.json()["pending_owner_id"] is None
    client.post("/auth/logout")
    _admin(client)
    own = client.post(f"/api/leads/{lead['id']}/assign", json={"user_id": me})
    assert own.status_code == 200
    assert own.json()["owner_id"] == me
    assert own.json()["pending_owner_id"] is None
    events = client.get(f"/api/leads/{lead['id']}/activity").json()["events"]
    text = " ".join(event["summary"] for event in events).lower()
    assert "offered" in text
    assert "declined" in text
    assert "accepted" in text
