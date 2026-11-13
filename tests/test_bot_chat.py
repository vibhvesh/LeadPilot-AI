"""Talk to Bots: approval gating, messages, and token auth."""

import httpx

from app.core.config import get_settings
from tests.helpers import login


def _admin(client):
    response = login(client, "vibhvesh@gmail.com", "Vibhvesh")
    assert response.status_code == 200


def _token(client) -> str:
    created = client.post("/api/settings/bot-tokens", json={"name": "Talk bot"})
    assert created.status_code == 200
    return created.json()["token"]


def _approve_member(client, email):
    login(client, email, "Member")
    _admin(client)
    users = client.get("/api/users").json()["users"]
    member = next(user for user in users if user["email"] == email)
    assert client.post(f"/api/users/{member['id']}/decision", json={"decision": "approve"}).status_code == 200


def test_unapproved_bot_cannot_chat_and_messages_flow_after_approval(client, monkeypatch):
    _admin(client)
    raw = _token(client)
    headers = {"Authorization": f"Bearer {raw}"}
    _approve_member(client, "member@example.com")
    captured = {}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr("app.bot.chat.httpx.Client", FakeClient)
    monkeypatch.setenv("GROKBOT_WEBHOOK_SECRET", "chat-secret")
    get_settings.cache_clear()

    assert client.post("/api/bot/connect", json={"name": "Grok"}).status_code == 401
    connect = client.post("/api/bot/connect", headers=headers, json={
        "name": "Grok Bot",
        "description": "Finds leads",
        "avatar_url": "https://cdn.example/bot.png",
        "webhook_url": "https://bot.example/talk",
        "user_email": "member@example.com",
    })
    assert connect.status_code == 200
    connection_id = connect.json()["id"]
    assert connect.json()["status"] == "pending"
    assert client.get("/api/bot/messages", headers=headers).status_code == 403
    assert client.post("/api/bot/messages", headers=headers, json={"text": "hello"}).status_code == 403

    client.post("/auth/logout")
    login(client, "other@example.com", "Other")
    _admin(client)
    _approve_member(client, "other@example.com")
    login(client, "other@example.com", "Other")
    assert client.post(f"/api/bots/{connection_id}/decision", json={"decision": "approve"}).status_code == 404
    client.post("/auth/logout")
    login(client, "member@example.com", "Member")
    approved = client.post(f"/api/bots/{connection_id}/decision", json={"decision": "approve"})
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    reply = client.post("/api/bot/messages", headers=headers, json={
        "text": "Three hospitals",
        "cards": [{"type": "leads", "title": "Suggested", "leads": [{"company": "City Hospital", "email": "desk@city.example", "city": "Ahmedabad"}]}],
    })
    assert reply.status_code == 200
    assert reply.json()["cards"][0]["leads"][0]["company"] == "City Hospital"
    assert client.get("/api/bots/unread").json()["unread"] == 1
    messages = client.get(f"/api/bots/{connection_id}/messages").json()
    assert messages[-1]["text"] == "Three hospitals"
    assert client.get("/api/bots/unread").json()["unread"] == 0

    sent = client.post(f"/api/bots/{connection_id}/messages", json={"text": "Add the first one"})
    assert sent.status_code == 200
    assert captured["url"] == "https://bot.example/talk"
    assert captured["json"]["text"] == "Add the first one"
    assert captured["json"]["sender"] == "user"
    assert captured["headers"]["X-LeadPilot-Webhook-Secret"] == "chat-secret"
    newer = client.get(f"/api/bot/messages?since={reply.json()['id']}", headers=headers)
    assert newer.status_code == 200
    assert newer.json()[-1]["text"] == "Add the first one"
    assert newer.json()[-1]["sender"] == "user"

    blocked = client.post(f"/api/bots/{connection_id}/decision", json={"decision": "block"})
    assert blocked.json()["status"] == "blocked"
    assert client.post("/api/bot/messages", headers=headers, json={"text": "still here"}).status_code == 403
    client.post("/auth/logout")
    _admin(client)
    activity = client.get("/api/activity").json()
    actions = {event["action"] for event in activity}
    assert "bot_approved" in actions
    assert "bot_blocked" in actions
    get_settings.cache_clear()


def test_bad_bot_token_cannot_connect(client):
    assert client.get("/api/bot/messages", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.post("/api/bot/messages", headers={"Authorization": "Bearer nope"}, json={"text": "hi"}).status_code == 401
