"""The corner cast is local SVG, stays click-through, and can point at the page."""

import subprocess
from pathlib import Path

from tests.helpers import login

ROOT = Path(__file__).resolve().parents[1]


def test_mascot_modules_are_served_with_the_app(client):
    assert login(client, "vibhvesh@gmail.com", "Vibhvesh").status_code == 200
    page = client.get("/")
    assert page.status_code == 200
    for name in (
        "mascot-characters.js",
        "mascot-characters.css",
        "mascot-idle.js",
        "mascot-idle.css",
        "mascot-insights.js",
        "mascot-insights.css",
        "mascot.js",
        "mascot.css",
    ):
        assert name in page.text
        asset = client.get("/static/" + name)
        assert asset.status_code == 200, name

    shell = client.get("/static/mascot.js").text
    assert "Hanuman" in shell
    assert "leadpilot-hanuman" in shell
    assert "leadpilot:mascot" in shell
    assert "Hide" in shell
    assert 'class="hanuman-hide"' in shell
    assert 'class="hanuman-option"' in shell

    cast = client.get("/static/mascot-characters.js").text
    assert "hanuman-crown" in cast
    assert "hanuman-gada" in cast
    assert "hanuman-tail" in cast
    assert "hanuman-tilak" in cast
    assert "leadpilot-mascot-character" in cast
    assert "new lead" in cast
    assert "waiting for access" in cast
    assert "Here's the summary!" in cast
    for name in ("Mango", "Noodle", "Pickle", "Biscuit"):
        assert name in cast

    sheet = client.get("/static/mascot.css").text
    assert "pointer-events: none" in sheet
    assert "pointer-events: auto" in sheet
    assert "prefers-reduced-motion" in sheet
    assert ".hanuman.is-fixed" in sheet

    motions = "\n".join(
        client.get(path).text
        for path in (
            "/static/mascot-characters.css",
            "/static/mascot-idle.css",
            "/static/mascot-insights.css",
        )
    )
    assert "@keyframes hanuman-hop" in motions
    assert "@keyframes mascot-wink" in motions
    assert "@keyframes mascot-scratch" in motions
    assert "@keyframes mascot-walk" in motions
    assert "mascot-spotlight" in motions
    assert motions.count("prefers-reduced-motion") >= 3

    idle = client.get("/static/mascot-idle.js").text
    assert "2600" in idle
    assert "8000" in idle
    insights = client.get("/static/mascot-insights.js").text
    assert "follow-up" in insights or "followup" in insights
    assert "Contacted" in insights
    assert "No LLM" in insights

    app = client.get("/static/app.js").text
    assert "data-score" in app
    assert "data-fu-id" in app
    assert "data-configured" in app
    assert "data-report" in app
    assert "data-account-status" in app


def test_mascot_choice_and_idle_rules():
    script = ROOT / "tests" / "mascot_logic.test.mjs"
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    for name in ("deeplink.test.mjs", "mascot_cast.test.mjs"):
        result = subprocess.run(["node", str(ROOT / "tests" / name)], capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr
