"""Packaging checks that do not need a running Docker daemon."""

from pathlib import Path

from app.core.config import Settings

ROOT = Path(__file__).resolve().parents[1]


def test_env_example_lists_every_setting():
    text = (ROOT / ".env.example").read_text()
    missing = [name.upper() for name in Settings.model_fields if f"{name.upper()}=" not in text]
    assert missing == []


def test_env_example_has_no_live_secrets():
    text = (ROOT / ".env.example").read_text()
    for line in text.splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.endswith("_KEY") or key.endswith("_SECRET") or key == "DB_PASSWORD":
            assert value == "" or value.startswith("replace-with-"), key


def test_dockerfile_runs_as_non_root_and_checks_health():
    text = (ROOT / "Dockerfile").read_text()
    assert "USER appuser" in text
    assert "HEALTHCHECK" in text
    assert "/health" in text
    assert "python:3.12.16-slim" in text


def test_compose_defines_app_postgres_and_proxy():
    text = (ROOT / "docker-compose.yml").read_text()
    assert "image: postgres:16.16-alpine" in text
    assert "leadpilot_db:" in text
    assert "pg_isready" in text
    assert "condition: service_healthy" in text
    assert "./deploy/proxy:/opt/leadpilot-proxy:ro" in text
    assert "/opt/leadpilot-proxy/entrypoint.sh" in text
    assert "127.0.0.1:${LEADPILOT_APP_PORT:-1102}:1102" in text


def test_ops_scripts_are_bash():
    for name in ("install-docker-ubuntu.sh", "backup.sh", "restore.sh"):
        script = ROOT / "scripts" / name
        assert script.is_file()
        assert script.read_text().startswith("#!/usr/bin/env bash\n")
