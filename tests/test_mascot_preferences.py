"""Mascot preferences are stored per person. Members see the cast on every signed-in page."""

from sqlalchemy import create_engine, inspect, text

from app.core.database import Base
from app.mascot.preferences import CHARACTERS
from app.mascot.schema import upgrade
from tests.helpers import login


def _approve(client, email, name):
    login(client, email, name)
    login(client, "vibhvesh@gmail.com", "Vibhvesh")
    users = client.get("/api/users").json()["users"]
    person = next(user for user in users if user["email"] == email)
    assert client.post(f"/api/users/{person['id']}/decision", json={"decision": "approve"}).status_code == 200
    client.post("/auth/logout")
    assert login(client, email, name).status_code == 200


def test_upgrade_adds_preference_columns(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    import app.models  # noqa: F401

    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users_old AS SELECT id, email FROM users"))
        connection.execute(text("DROP TABLE users"))
        connection.execute(text("ALTER TABLE users_old RENAME TO users"))
        connection.execute(text("CREATE TABLE workspace_old AS SELECT id, workspace_name FROM workspace_settings"))
        connection.execute(text("DROP TABLE workspace_settings"))
        connection.execute(text("ALTER TABLE workspace_old RENAME TO workspace_settings"))
    upgrade(engine)
    user_columns = {column["name"] for column in inspect(engine).get_columns("users")}
    workspace_columns = {column["name"] for column in inspect(engine).get_columns("workspace_settings")}
    assert "preferences" in user_columns
    assert "mascot_character" in workspace_columns
    assert upgrade(engine) == []


def test_member_saves_preferences_and_sees_the_mascot(client):
    _approve(client, "pilot@example.com", "Pilot")
    page = client.get("/")
    assert page.status_code == 200
    for name in (
        "/static/mascot.js",
        "/static/mascot.css",
        "/static/mascot-characters.js",
        "/static/mascot-ramayana.js",
        "/static/mascot-mahabharata.js",
        "/static/mascot-settings.js",
        "/static/mascot-settings.css",
    ):
        assert name in page.text
    home = page.text
    assert 'id="mascot-settings-open"' in home
    prefs = client.get("/api/me/preferences")
    assert prefs.status_code == 200
    assert prefs.json()["enabled"] is True
    assert prefs.json()["character"] == "hanuman"
    assert prefs.json()["can_set_default"] is False
    saved = client.put("/api/me/preferences", json={
        "character": "krishna",
        "enabled": False,
        "idle_ms": 1500,
        "tone": "polite",
        "size": "large",
        "side": "left",
    })
    assert saved.status_code == 200
    body = saved.json()
    assert body["character"] == "krishna"
    assert body["enabled"] is False
    assert body["idle_ms"] == 1500
    assert body["tone"] == "polite"
    assert body["size"] == "large"
    assert body["side"] == "left"
    assert body["explicit"] is True
    again = client.get("/api/me/preferences").json()
    assert again["character"] == "krishna"
    assert client.put("/api/me/preferences", json={"idle_ms": 500}).status_code == 400
    assert client.put("/api/me/preferences", json={"character": "not-a-person"}).status_code == 400
    assert client.put("/api/settings/mascot", json={"character": "rama"}).status_code == 403

    client.post("/auth/logout")
    login(client, "vibhvesh@gmail.com", "Vibhvesh")
    assert client.put("/api/settings/mascot", json={"character": "rama"}).status_code == 200
    client.post("/auth/logout")
    login(client, "pilot@example.com", "Pilot")
    fresh = client.get("/api/me/preferences").json()
    assert fresh["character"] == "krishna"
    assert fresh["workspace_default"] == "rama"
    assert set(CHARACTERS) >= {"hanuman", "rama", "krishna", "ravana", "ghatotkacha", "rocket-boss"}


def test_hanuman_is_the_fallback_and_a_saved_character_stays(client):
    from app.core.database import SessionLocal
    from app.models.workspace import WorkspaceSettings

    assert login(client, "vibhvesh@gmail.com", "Vibhvesh").status_code == 200
    fresh = client.get("/api/me/preferences").json()
    assert fresh["character"] == "hanuman"
    assert fresh["workspace_default"] == "hanuman"
    assert fresh["family_friendly"] is False
    db = SessionLocal()
    try:
        row = db.get(WorkspaceSettings, 1)
        row.mascot_character = "not-a-mascot"
        db.commit()
    finally:
        db.close()
    fallback = client.get("/api/me/preferences").json()
    assert fallback["character"] == "hanuman"
    assert fallback["workspace_default"] == "hanuman"
    kept = client.put("/api/me/preferences", json={"character": "biscuit"})
    assert kept.status_code == 200
    assert kept.json()["character"] == "biscuit"
    db = SessionLocal()
    try:
        row = db.get(WorkspaceSettings, 1)
        row.mascot_character = "hanuman"
        db.commit()
    finally:
        db.close()
    assert client.get("/api/me/preferences").json()["character"] == "biscuit"
    forced = client.put("/api/settings/mascot", json={"family_friendly": True})
    assert forced.status_code == 200
    assert forced.json()["family_friendly"] is True
    assert client.get("/api/me/preferences").json()["family_friendly"] is True
    assert client.get("/api/me/preferences").json()["family_friendly_forced"] is True
