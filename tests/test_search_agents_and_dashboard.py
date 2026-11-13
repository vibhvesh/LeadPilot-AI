from tests.helpers import login


def _admin(client):
    response = login(client, "vibhvesh@gmail.com", "Vibhvesh")
    assert response.status_code == 200
    return response


def test_search_creates_leads_and_second_run_dedupes(client):
    _admin(client)
    saved = client.post("/api/search/criteria", json={
        "name": "US logistics",
        "industry": "logistics",
        "keywords": "freight",
        "country": "United States",
        "state": "California",
        "results_limit": 10,
    })
    assert saved.status_code == 200
    criteria_id = saved.json()["id"]
    first = client.post(f"/api/search/criteria/{criteria_id}/run")
    assert first.status_code == 200
    body = first.json()
    assert body["provider"] == "mock"
    assert body["created_count"] >= 1
    assert body["duplicate_count"] == 0
    second = client.post(f"/api/search/criteria/{criteria_id}/run")
    assert second.status_code == 200
    assert second.json()["created_count"] == 0
    assert second.json()["duplicate_count"] >= 1
    leads = client.get("/api/leads").json()
    assert any(lead["company"] == "Northstar Logistics" for lead in leads)
    assert all(lead["status"] == "New" for lead in leads)


def test_unknown_profile_still_returns_stable_demo_leads(client):
    _admin(client)
    saved = client.post("/api/search/criteria", json={
        "name": "Widgets",
        "industry": "specialty-widgets",
        "country": "India",
        "state": "Gujarat",
        "city": "Vadodara",
        "results_limit": 5,
    })
    criteria_id = saved.json()["id"]
    first = client.post(f"/api/search/criteria/{criteria_id}/run").json()
    assert first["created_count"] == 5
    again = client.post(f"/api/search/criteria/{criteria_id}/run").json()
    assert again["created_count"] == 0
    assert again["duplicate_count"] == 5


def test_pipeline_scores_without_qualifying_until_review(client):
    _admin(client)
    created = client.post("/api/leads", json={
        "company": "Harbour Test Co",
        "contact_name": "Priya Shah",
        "email": "priya@harbourtest.example",
        "website": "https://harbourtest.example",
        "industry": "professional services",
        "country": "India",
        "state": "Gujarat",
        "city": "Vadodara",
        "notes": "Hiring operations managers. Contact priya@harbourtest.example",
    })
    assert created.status_code == 200
    lead_id = created.json()["id"]
    blocked = client.patch(f"/api/leads/{lead_id}", json={"status": "Qualified"})
    assert blocked.status_code == 400
    run = client.post("/api/agents/run", json={"lead_id": lead_id})
    assert run.status_code == 200
    body = run.json()
    assert body["delivery"] == "draft"
    assert body["outreach"]["delivery"] == "draft"
    assert "draft" in body["outreach"]["body"].lower()
    assert isinstance(body["score"], int)
    assert body["lead_status"] in (None, "New")
    agents = [step["agent"] for step in body["steps"]]
    assert agents[:6] == ["orchestrator", "research", "enrichment", "quality", "qualification", "outreach"]
    current = client.get(f"/api/leads/{lead_id}").json()
    assert current["status"] == "New"
    assert current["score"] == body["score"]
    review = client.post(f"/api/leads/{lead_id}/review", json={"decision": "qualify", "note": "Looks like a fit"})
    assert review.status_code == 200
    assert review.json()["status"] == "Qualified"
    assert review.json()["human_reviewed"] is True
    assert client.post("/api/agents/send", json={"lead_id": lead_id}).status_code == 404


def test_dashboard_and_activity_use_database_counts(client):
    _admin(client)
    client.post("/api/leads", json={"company": "Counted One", "country": "India", "estimated_value": 100000, "website": "https://counted-one.example"})
    second = client.post("/api/leads", json={"company": "Counted Two", "country": "India", "estimated_value": 50000, "website": "https://counted-two.example"}).json()
    client.post(f"/api/leads/{second['id']}/review", json={"decision": "qualify"})
    dashboard = client.get("/api/dashboard").json()
    assert dashboard["total_leads"] == 2
    assert dashboard["qualified_leads"] == 1
    assert dashboard["pipeline_value"] == 150000
    assert dashboard["admin"]["pending"] == 0
    reports = client.get("/api/reports").json()
    assert reports["leads_this_month"] == 2
    activity = client.get("/api/activity").json()
    assert any(event["action"] == "sign_in" for event in activity)
    summary = client.get("/api/activity/summary").json()
    assert summary["activities_today"] >= 1


def test_provider_key_is_stored_encrypted_and_not_returned(client):
    _admin(client)
    secret = "sk-test-secret-value"
    saved = client.put("/api/providers/keys", json={"provider": "openai", "api_key": secret})
    assert saved.status_code == 200
    assert secret not in saved.text
    assert saved.json()["hint"].endswith("alue")
    listing = client.get("/api/providers")
    assert secret not in listing.text
    openai = next(row for row in listing.json()["keys"] if row["provider"] == "openai")
    assert openai["configured"] is True
    assert openai["source"] == "database"
    from app.core.database import SessionLocal
    from app.providers.secrets import resolve_secret

    db = SessionLocal()
    try:
        assert resolve_secret(db, "openai", "") == secret
    finally:
        db.close()


def test_quota_blocks_the_next_search(client):
    _admin(client)
    login(client, "scout@example.com", "Scout")
    login(client, "vibhvesh@gmail.com", "Vibhvesh")
    users = client.get("/api/users").json()["users"]
    scout = next(user for user in users if user["email"] == "scout@example.com")
    client.post(f"/api/users/{scout['id']}/decision", json={"decision": "approve"})
    access = client.put("/api/providers/access", json={
        "provider": "mock",
        "role": "member",
        "enabled": True,
        "daily_quota": 1,
        "monthly_quota": 1,
    })
    assert access.status_code == 200
    client.post("/auth/logout")
    login(client, "scout@example.com", "Scout")
    saved = client.post("/api/search/criteria", json={"name": "Open search", "industry": "retail", "country": "United States"})
    criteria_id = saved.json()["id"]
    first = client.post(f"/api/search/criteria/{criteria_id}/run")
    assert first.status_code == 200
    second = client.post(f"/api/search/criteria/{criteria_id}/run")
    assert second.status_code == 429


def test_normalize_dedup_and_contact_extraction():
    from app.search.normalize import clean_title, dedup_key, extract_email
    from app.search.providers import parse_tavily_results

    assert dedup_key("Northstar Logistics", "https://www.northstar.example/about") == "domain:northstar.example"
    assert dedup_key("Northstar Logistics", "https://linkedin.com/company/northstar").startswith("name:")
    assert extract_email("Write ada@acme.example for a demo") == "ada@acme.example"
    assert clean_title("Acme Robotics | LinkedIn") == "Acme Robotics"
    rows = parse_tavily_results({"results": [{"title": "Acme Robotics - Home", "url": "https://acme.example", "content": "Email ada@acme.example"}]})
    assert rows[0]["company"] == "Acme Robotics"
    assert rows[0]["email"] == "ada@acme.example"
    assert rows[0]["website"] == "https://acme.example"
