"""The browser tab uses Rocket Boss's face, without the cigar."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app" / "web"


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def test_favicon_is_linked_and_has_no_cigar(client):
    login = client.get("/login")
    assert login.status_code == 200
    for piece in (
        "/static/favicon.svg",
        "/static/favicon-32.png",
        "/static/favicon-16.png",
        "/static/apple-touch-icon.png",
        "/static/site.webmanifest",
    ):
        assert piece in login.text
    home = client.get("/", follow_redirects=False)
    assert home.status_code == 302
    icon = client.get("/favicon.ico")
    assert icon.status_code == 200
    assert icon.headers["content-type"].startswith("image/")
    svg = (ROOT / "favicon.svg").read_text()
    assert "cigar" not in svg.lower()
    assert "smoke" not in svg.lower()
    assert _png_size(ROOT / "favicon-16.png") == (16, 16)
    assert _png_size(ROOT / "favicon-32.png") == (32, 32)
    assert _png_size(ROOT / "apple-touch-icon.png") == (180, 180)
    assert _png_size(ROOT / "icon-192.png") == (192, 192)
    manifest = client.get("/static/site.webmanifest")
    assert manifest.status_code == 200
    assert "icon-192.png" in manifest.text
