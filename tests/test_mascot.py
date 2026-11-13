"""The Hanuman mascot is a local SVG module and stays out of the way."""

from tests.helpers import login


def test_mascot_module_is_served_with_the_app(client):
    assert login(client, "vibhvesh@gmail.com", "Vibhvesh").status_code == 200
    page = client.get("/")
    assert page.status_code == 200
    assert "mascot.js" in page.text
    assert "mascot.css" in page.text

    script = client.get("/static/mascot.js")
    assert script.status_code == 200
    body = script.text
    assert "Hanuman" in body
    assert "hanuman-crown" in body
    assert "hanuman-gada" in body
    assert "hanuman-tail" in body
    assert "hanuman-tilak" in body
    assert "leadpilot-hanuman" in body
    assert "new lead" in body
    assert "waiting for access" in body
    assert "Here's the summary!" in body

    css = client.get("/static/mascot.css")
    assert css.status_code == 200
    sheet = css.text
    assert "pointer-events: none" in sheet
    assert "pointer-events: auto" in sheet
    assert "prefers-reduced-motion" in sheet
    assert "@keyframes hanuman-hop" in sheet
