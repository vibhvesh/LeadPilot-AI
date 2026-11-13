"""Pipeline cards deep-link to a lead, and a status change moves the column."""

from tests.helpers import login


def _admin(client):
    response = login(client, "vibhvesh@gmail.com", "Vibhvesh")
    assert response.status_code == 200
    return response


def test_status_filter_and_lead_detail_follow_a_column_move(client):
    _admin(client)
    created = client.post("/api/leads", json={
        "company": "Tap Target Co",
        "city": "Austin",
        "state": "Texas",
        "country": "United States",
    })
    assert created.status_code == 200
    lead_id = created.json()["id"]

    board = client.get("/api/pipeline").json()
    card = next(item for item in board["columns"]["New"] if item["id"] == lead_id)
    assert card["company"] == "Tap Target Co"
    assert "Austin" in card["region"]
    assert any(item["id"] == lead_id for item in client.get("/api/leads", params={"status": "New"}).json())
    assert all(item["id"] != lead_id for item in client.get("/api/leads", params={"status": "Contacted"}).json())

    detail = client.get(f"/api/leads/{lead_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "New"

    moved = client.patch(f"/api/leads/{lead_id}", json={"status": "Contacted"})
    assert moved.status_code == 200
    assert moved.json()["status"] == "Contacted"
    board = client.get("/api/pipeline").json()
    assert any(item["id"] == lead_id for item in board["columns"]["Contacted"])
    assert all(item["id"] != lead_id for item in board["columns"]["New"])
    assert client.get("/api/leads", params={"status": "Contacted"}).json()[0]["id"] == lead_id

    blocked = client.patch(f"/api/leads/{lead_id}", json={"status": "Qualified"})
    assert blocked.status_code == 400
    reviewed = client.post(f"/api/leads/{lead_id}/review", json={"decision": "qualify"})
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "Qualified"
    assert any(item["id"] == lead_id for item in client.get("/api/pipeline").json()["columns"]["Qualified"])


def test_leads_deep_link_serves_the_app_and_pipeline_cards_are_links(client):
    _admin(client)
    page = client.get("/leads?id=1")
    assert page.status_code == 200
    assert "pipeline-ui.js" in page.text
    script = client.get("/static/pipeline-ui.js")
    assert script.status_code == 200
    assert "/leads?id=" in script.text
    assert "/leads?status=" in script.text
    assert "mini-link" in script.text
    client.post("/auth/logout")
    guest = client.get("/leads?status=New", follow_redirects=False)
    assert guest.status_code == 302
    assert guest.headers["location"] == "/login"
