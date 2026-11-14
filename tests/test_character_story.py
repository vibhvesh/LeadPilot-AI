"""Admin Ramayana story page, editable lines, and the overlay switch."""

import struct
import subprocess
from pathlib import Path

from tests.helpers import login

ROOT = Path(__file__).resolve().parents[1]


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


def test_story_page_is_admin_only_and_stays_off_the_rest_of_the_app(client):
    signed_out = client.get("/admin/character-story", follow_redirects=False)
    assert signed_out.status_code == 302
    assert signed_out.headers["location"] == "/login"
    alias = client.get("/admin/idle-characters", follow_redirects=False)
    assert alias.status_code == 302
    assert alias.headers["location"] == "/login"

    _member(client)
    assert client.get("/admin/character-story").status_code == 403
    assert client.get("/admin/idle-characters").status_code == 403
    assert client.put("/api/admin/story-messages", json={"scene_id": "s01", "actor": "narad", "text": "Nope"}).status_code == 403

    client.post("/auth/logout")
    _admin(client)
    page = client.get("/admin/character-story")
    assert page.status_code == 200
    assert "Play now" in page.text
    assert "story-crew.js" in page.text
    assert "v=crew1" in page.text
    assert "ramayana-story.js" not in page.text
    assert "mascot-crew.js" not in page.text
    jumped = client.get("/admin/idle-characters", follow_redirects=False)
    assert jumped.status_code == 302
    assert jumped.headers["location"] == "/admin/character-story"

    shell = (ROOT / "app/web/index.html").read_text()
    assert 'href="/admin/character-story"' in shell
    assert "story-boot.js" not in shell
    assert "ramayana-story.js" not in shell
    crew = (ROOT / "app/web/mascot-crew.js").read_text()
    assert "60000" in crew
    boot = (ROOT / "app/web/story-boot.js").read_text()
    assert "120000" in boot
    assert "?v=" in boot
    assert "?v=" in page.text
    assert "getDisplayMedia" not in (ROOT / "app/web/story-overlay.js").read_text()
    sprites = list((ROOT / "app/web/story").glob("*.png"))
    assert len(sprites) == 20
    for sprite in sprites:
        assert sprite.stat().st_size < 80 * 1024
        raw = sprite.read_bytes()
        assert raw[12:16] == b"IHDR"
        width, height = struct.unpack(">II", raw[16:24])
        assert 0.15 < width / height < 0.75, sprite.name


def test_lines_save_reset_and_overlay_defaults_off(client):
    _admin(client)
    assert client.get("/api/story/overlay").json()["enabled"] is False
    turned = client.put("/api/admin/story-overlay", json={"enabled": True})
    assert turned.status_code == 200
    assert turned.json()["enabled"] is True
    assert client.put("/api/admin/story-overlay", json={"enabled": False}).json()["enabled"] is False

    blessing = client.put("/api/admin/story-messages", json={"scene_id": "s01", "actor": "valmiki", "text": "Aashirvad, beta."})
    assert blessing.status_code == 200
    assert client.get("/api/story/lines").json()["lines"]["s01:valmiki"] == "Aashirvad, beta."
    assert client.post("/api/admin/story-messages/reset", json={"scene_id": "s01", "actor": "valmiki"}).status_code == 200

    saved = client.put("/api/admin/story-messages", json={"scene_id": "s04", "actor": "old-man-boss", "text": "Plan badlo."})
    assert saved.status_code == 200
    assert client.get("/api/story/lines").json()["lines"]["s04:old-man-boss"] == "Plan badlo."
    assert client.post("/api/admin/story-messages/reset", json={"scene_id": "s04", "actor": "old-man-boss"}).status_code == 200
    assert "s04:old-man-boss" not in client.get("/api/story/lines").json()["lines"]
    assert client.put("/api/admin/story-messages", json={"scene_id": "nope", "actor": "narad", "text": "x"}).status_code == 400


def test_story_script_rules():
    for name in ("ramayana_story.test.mjs", "story_crew.test.mjs"):
        result = subprocess.run(["node", str(ROOT / "tests" / name)], capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr
