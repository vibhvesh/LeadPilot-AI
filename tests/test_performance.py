"""Performance samples, retention, and the admin-only error log."""

from datetime import timedelta

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.identity import utcnow
from app.models.perf import AppErrorGroup, PerfSample
from app.perf.collector import collect_sample, purge
from app.perf.errors import reset_rate_limit
from tests.helpers import login


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


def test_collector_writes_a_sample_and_purge_drops_old_rows(client):
    _admin(client)
    db = SessionLocal()
    try:
        row = collect_sample(db)
        assert row.id
        assert row.memory_total > 0
        assert row.cpu_percent >= 0
        old = PerfSample(sampled_at=utcnow() - timedelta(days=9), cpu_percent=1)
        db.add(old)
        db.commit()
        removed = purge(db, perf_days=5, error_days=30)
        assert removed["samples"] >= 1
        ids = set(db.scalars(select(PerfSample.id)).all())
        assert row.id in ids
        assert old.id not in ids
    finally:
        db.close()
    current = client.get("/api/admin/perf/current")
    assert current.status_code == 200
    assert current.json()["sample"]["memory_total"] > 0
    history = client.get("/api/admin/perf/history?range=1h")
    assert history.status_code == 200
    assert history.json()["samples"]


def test_server_errors_are_stored_and_404s_are_counted(client):
    from app.main import app

    if not any(getattr(route, "path", None) == "/api/__perf_boom" for route in app.routes):
        @app.get("/api/__perf_boom")
        def _boom():
            raise RuntimeError("perf boom")

    _admin(client)
    failed = client.get("/api/__perf_boom")
    assert failed.status_code == 500
    missing = client.get("/api/__perf_missing")
    assert missing.status_code == 404
    client.get("/api/__perf_missing")
    groups = client.get("/api/admin/errors").json()["errors"]
    boom = next(row for row in groups if "perf boom" in row["message"])
    assert boom["count"] >= 1
    assert boom["source"] == "server"
    detail = client.get(f"/api/admin/errors/{boom['id']}")
    assert detail.status_code == 200
    assert "RuntimeError" in detail.json()["sample_trace"]
    assert detail.json()["occurrences"]
    resolved = client.post(f"/api/admin/errors/{boom['id']}/resolve", json={"resolved": True})
    assert resolved.json()["resolved"] is True
    not_found = next(row for row in groups if row["status_code"] == 404)
    assert not_found["count"] >= 2


def test_login_redirects_are_not_stored_as_errors(client):
    assert client.get("/api/me").status_code == 401
    _admin(client)
    groups = client.get("/api/admin/errors").json()["errors"]
    assert all(row["status_code"] != 401 for row in groups)


def test_client_errors_require_auth_and_are_rate_limited(client, monkeypatch):
    assert client.post("/api/client-errors", json={"message": "nope"}).status_code == 401
    _member(client)
    reset_rate_limit()
    monkeypatch.setattr("app.perf.router.get_settings", lambda: type("S", (), {"client_error_per_minute": 2})())
    assert client.post("/api/client-errors", json={"message": "one", "stack": "Error: one"}).status_code == 200
    assert client.post("/api/client-errors", json={"message": "two"}).status_code == 200
    limited = client.post("/api/client-errors", json={"message": "three"})
    assert limited.status_code == 429
    huge = "x" * 9000
    assert client.post("/api/client-errors", json={"message": huge}).status_code == 413
    client.post("/auth/logout")
    _admin(client)
    rows = client.get("/api/admin/errors?source=client").json()["errors"]
    assert any(row["source"] == "client" and row["count"] >= 1 for row in rows)


def test_members_cannot_open_performance(client):
    _member(client)
    assert client.get("/api/admin/perf/current").status_code == 403
    assert client.get("/api/admin/perf/history").status_code == 403
    assert client.get("/api/admin/errors").status_code == 403
    page = client.get("/admin/performance")
    assert page.status_code == 403
    client.post("/auth/logout")
    _admin(client)
    opened = client.get("/admin/performance")
    assert opened.status_code == 200
    assert 'data-tab="performance"' in opened.text
    assert 'data-admin-only' in opened.text
    assert 'id="performance-home-link"' in opened.text
    assert 'href="/admin/performance"' in opened.text
    assert 'src="/static/cockpit/performance.js"' in opened.text
