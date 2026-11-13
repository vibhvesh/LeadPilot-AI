import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SESSION_SECRET"] = "test-secret-key-at-least-32-characters-long"
os.environ["DEMO_MODE"] = "true"
os.environ["SESSION_COOKIE_SECURE"] = "false"
os.environ["SUPER_ADMIN_EMAIL"] = "vibhvesh@gmail.com"
os.environ["APP_ENV"] = "test"
os.environ["SEARCH_PROVIDER"] = "auto"

import pytest
from fastapi.testclient import TestClient

from app.core import database
from app.main import app


@pytest.fixture
def client():
    database.Base.metadata.drop_all(database.engine)
    database.Base.metadata.create_all(database.engine)
    with TestClient(app) as test_client:
        yield test_client


