"""Games tab: signed-in route, workspace nav, chess iframe, and frame policy."""

from tests.helpers import login


def test_games_route_and_nav(client):
    guest = client.get("/games", follow_redirects=False)
    assert guest.status_code == 302
    assert guest.headers["location"] == "/login"

    assert login(client, "vibhvesh@gmail.com", "Vibhvesh").status_code == 200
    page = client.get("/games")
    assert page.status_code == 200
    workspace = page.text.split("ADMINISTRATION", 1)[0]
    assert 'data-tab="games"' in workspace
    assert "♟ Games" in workspace
    assert 'src="https://vibhvesh.github.io/chess-live/"' in page.text
    assert 'allow="microphone; autoplay; clipboard-write"' in page.text
    assert 'href="https://vibhvesh.github.io/chess-live/"' in page.text
    assert 'target="_blank"' in page.text
    assert "Open full screen" in page.text

    policy = page.headers["content-security-policy"]
    assert "frame-src" in policy
    assert "https://vibhvesh.github.io" in policy
    permissions = page.headers["permissions-policy"]
    assert "microphone" in permissions
    assert "https://vibhvesh.github.io" in permissions

    script = client.get("/static/app.js").text
    assert 'games: "games"' in script
    assert 'module === "games"' in script
    home = client.get("/")
    assert 'data-tab="games"' in home.text.split("ADMINISTRATION", 1)[0]
    assert "frame-src" in home.headers["content-security-policy"]
