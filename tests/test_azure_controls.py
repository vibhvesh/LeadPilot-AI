"""Azure controls replace native pickers and window.confirm."""

from tests.helpers import login


def test_themed_controls_are_served(client):
    assert login(client, "vibhvesh@gmail.com", "Vibhvesh").status_code == 200
    page = client.get("/")
    assert page.status_code == 200
    for name in ("theme.css", "select.css", "select.js", "controls.js", "dialog.js"):
        assert name in page.text
        assert client.get("/static/" + name).status_code == 200

    select = client.get("/static/select.js").text
    assert 'role="listbox"' in select or "listbox" in select
    assert "ArrowDown" in select
    assert "Escape" in select
    assert "aria-selected" in select
    assert "is-sheet" in select

    theme = client.get("/static/theme.css").text
    assert "--azure" in theme
    assert "prefers-reduced-motion" not in theme or "scrollbar" in theme
    assert 'input[type="checkbox"]' in theme
    assert 'input[type="radio"]' in theme
    assert 'input[type="file"]' in theme
    assert 'input[type="range"]' in theme
    assert 'input[type="datetime-local"]' in theme
    assert "scrollbar-color" in theme
    assert ":focus-visible" in theme
    assert "azure-toggle" in theme

    dialog = client.get("/static/dialog.js").text
    assert "alertdialog" in dialog
    assert "Escape" in dialog
    search = client.get("/static/search-ui.js").text
    assert "window.confirm" not in search
    assert "AzureDialog.confirm" in search

    sign_in = client.get("/login")
    assert "theme.css" in sign_in.text
