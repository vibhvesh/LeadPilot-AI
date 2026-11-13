"""Dropdown catalog, seeded presets, and admin editing. Presets are config, not leads."""

from app.search.presets import US_STATES, compose_query, merge_query_templates
from tests.fakes import install_fake_llm
from tests.helpers import login

REQUIRED_LABELS = [
    "Open US staffing RFPs (temp personnel)",
    "Travel nurse staffing bids",
    "IT staffing / C2C contracts – agencies welcome",
    "MSP programs accepting new suppliers",
    "Holiday/seasonal high-volume hiring",
    "New manufacturing plants hiring 500+",
    "Executive search RFPs (public sector)",
    "School district staffing RFPs",
    "Healthcare systems using vendors",
    "Government IT staffing contracts",
]


def _admin(client):
    response = login(client, "vibhvesh@gmail.com", "Vibhvesh")
    assert response.status_code == 200
    return response


def _member(client):
    _admin(client)
    login(client, "scout@example.com", "Scout")
    _admin(client)
    users = client.get("/api/users").json()["users"]
    scout = next(user for user in users if user["email"] == "scout@example.com")
    assert client.post(f"/api/users/{scout['id']}/decision", json={"decision": "approve"}).status_code == 200
    client.post("/auth/logout")
    assert login(client, "scout@example.com", "Scout").status_code == 200


def test_catalog_lists_states_and_seeded_presets(client):
    _admin(client)
    body = client.get("/api/search/presets").json()
    assert body["options"]["us_states"] == list(US_STATES)
    assert len(body["options"]["us_states"]) == 51
    assert "District of Columbia" in body["options"]["us_states"]
    assert body["options"]["countries"][0] == "United States"
    assert "Staffing/recruitment RFP or bid" in body["options"]["opportunity_types"]
    assert "Healthcare/Nursing" in body["options"]["role_categories"]
    labels = [preset["label"] for preset in body["presets"]]
    for label in REQUIRED_LABELS:
        assert label in labels
    staffing = next(preset for preset in body["presets"] if preset["slug"] == "open-us-staffing-rfps")
    assert any("site:bidnet" in item for item in staffing["query_templates"])
    assert any("request for proposal" in item and "staffing services" in item for item in staffing["query_templates"])
    c2c = next(preset for preset in body["presets"] if "C2C" in preset["label"])
    assert any("C2C" in item or "agencies welcome" in item for item in c2c["query_templates"])
    assert body["defaults"]["country"] == "United States"
    assert body["defaults"]["opportunity_type"] == "Staffing/recruitment RFP or bid"
    settings = client.get("/api/settings").json()
    assert settings["icp_country"] == "United States"
    assert "recruitment vendors" in settings["ideal_customer"]


def test_compose_query_uses_templates_and_selected_states():
    query = compose_query({
        "keywords": "freight",
        "industry": "logistics",
        "state": "California",
        "country": "United States",
    })
    assert "freight" in query and "logistics" in query and "California" in query and "companies" in query
    templated = compose_query({
        "country": "United States",
        "states": ["Texas", "Ohio"],
        "keywords": "nursing",
        "query_templates": ['"request for proposal" "staffing services"', "site:bidnet.com travel nurse"],
        "opportunity_type": "Staffing/recruitment RFP or bid",
    })
    assert "site:bidnet.com" in templated
    assert "Texas" in templated and "Ohio" in templated
    assert "companies" not in templated
    plan = merge_query_templates(
        {"queries": ["one", "two", "three"]},
        {"query_templates": ["site:bidnet.com temporary staffing"]},
    )
    assert plan["queries"][0] == "site:bidnet.com temporary staffing"
    assert len(plan["queries"]) == 4


def test_saved_search_keeps_structured_criteria_and_searches_with_templates(client, monkeypatch):
    captured = {}

    def choose(_db):
        return "tavily", "test-key"

    def tavily(_key, query, _limit):
        captured["query"] = query
        return []

    monkeypatch.setattr("app.search.providers.choose_search_provider", choose)
    monkeypatch.setattr("app.search.providers.tavily_search", tavily)
    _admin(client)
    saved = client.post("/api/search/criteria", json={
        "name": "Texas and Ohio nurses",
        "country": "United States",
        "states": ["Texas", "Ohio"],
        "opportunity_type": "Staffing/recruitment RFP or bid",
        "role_category": "Healthcare/Nursing",
        "keywords": "nursing",
        "query_templates": ['"request for proposal" "staffing services"', "site:bidnet.com travel nurse"],
        "posted_window": "open",
        "min_score": 55,
    })
    assert saved.status_code == 200
    body = saved.json()
    assert body["states"] == ["Texas", "Ohio"]
    assert body["min_score"] == 55
    assert body["posted_window"] == "open"
    rejected = client.post("/api/search/criteria", json={"name": "Not a state", "country": "United States", "states": ["Gujarat"]})
    assert rejected.status_code == 400
    allowed = client.post("/api/search/criteria", json={"name": "Gujarat clinics", "country": "India", "state": "Gujarat", "industry": "specialty-widgets"})
    assert allowed.status_code == 200
    assert allowed.json()["state"] == "Gujarat"
    run = client.post(f"/api/search/criteria/{body['id']}/run")
    assert run.status_code == 200
    assert "site:bidnet.com" in captured["query"]
    assert "Texas" in captured["query"] and "Ohio" in captured["query"]
    preview = client.post("/api/search/preview", json={"country": "United States", "keywords": "staffing", "states": []})
    assert preview.status_code == 200
    assert "United States" in preview.json()["query"]


def test_member_can_read_presets_but_only_admin_can_edit(client):
    _member(client)
    assert client.get("/api/search/presets").status_code == 200
    denied = client.post("/api/search/presets", json={"label": "Member preset", "country": "United States", "keywords": "staffing"})
    assert denied.status_code == 403
    client.post("/auth/logout")
    _admin(client)
    created = client.post("/api/search/presets", json={
        "label": "Warehouse surge",
        "country": "United States",
        "role_category": "Warehouse/Logistics",
        "keywords": "warehouse surge hiring",
        "query_templates": ["warehouse staffing agencies welcome"],
        "ai_text": "Find US warehouse hiring that is open to staffing agencies.",
    })
    assert created.status_code == 200
    preset_id = created.json()["id"]
    updated = client.put(f"/api/search/presets/{preset_id}", json={
        "label": "Warehouse surge hiring",
        "country": "United States",
        "keywords": "warehouse surge hiring",
        "query_templates": ["warehouse staffing agencies welcome"],
        "ai_text": "Find US warehouse hiring that is open to staffing agencies.",
    })
    assert updated.status_code == 200
    assert updated.json()["label"] == "Warehouse surge hiring"
    assert client.delete(f"/api/search/presets/{preset_id}").status_code == 200
    labels = [item["label"] for item in client.get("/api/search/presets").json()["presets"]]
    assert "Warehouse surge hiring" not in labels


def test_keyword_suggestions_include_presets_and_past_searches(client):
    _admin(client)
    assert client.post("/api/search/criteria", json={
        "name": "Past warehouse search",
        "country": "United States",
        "keywords": "warehouse surge hiring",
    }).status_code == 200
    suggestions = client.get("/api/search/suggestions", params={"q": "warehouse"}).json()["suggestions"]
    assert any("warehouse surge hiring" in item for item in suggestions)
    preset_hits = client.get("/api/search/suggestions", params={"q": "bidnet"}).json()["suggestions"]
    assert any("bidnet" in item.lower() for item in preset_hits)
    cities = client.get("/api/search/suggestions", params={"q": "Austin"}).json()["suggestions"]
    assert "Austin" in cities


def test_ai_search_uses_templates_and_minimum_score(client, monkeypatch):
    install_fake_llm(monkeypatch)

    def hits(_db, _query, limit=5):
        return [{
            "company": "Score Hospital",
            "email": "jobs@scorehospital.example",
            "website": "https://scorehospital.example",
            "source_url": "https://scorehospital.example/jobs",
            "snippet": "Score Hospital is hiring nurses.",
            "search_provider": "tavily",
            "country": "United States",
        }]

    monkeypatch.setattr("app.ai_search.runner.search_query", hits)
    _admin(client)
    low = client.post("/api/search/ai", json={
        "text": "Travel nurse staffing bids in the United States",
        "criteria": {
            "country": "United States",
            "min_score": 90,
            "query_templates": ["site:bidnet.com travel nurse staffing"],
        },
    })
    assert low.status_code == 200
    assert low.json()["created_count"] == 0
    assert "site:bidnet.com travel nurse staffing" in low.json()["plan"]["queries"]
    assert client.get("/api/leads").json() == []
    kept = client.post("/api/search/ai", json={
        "text": "Travel nurse staffing bids in the United States",
        "criteria": {"country": "United States", "min_score": 40},
    })
    assert kept.status_code == 200
    assert kept.json()["created_count"] == 1
    assert client.get("/api/leads").json()[0]["score"] == 72
