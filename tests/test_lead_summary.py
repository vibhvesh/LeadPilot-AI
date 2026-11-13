"""Lead detail data and the summary preview module."""

from tests.helpers import login


def test_lead_fields_and_summary_module_are_available(client):
    assert login(client, "vibhvesh@gmail.com", "Vibhvesh").status_code == 200
    created = client.post("/api/leads", json={
        "company": "Preview Hospital",
        "contact_name": "Priya Shah",
        "email": "priya@previewhospital.example",
        "phone": "+1-512-555-0100",
        "website": "https://previewhospital.example",
        "source_url": "https://previewhospital.example/jobs",
        "city": "Austin",
        "state": "Texas",
        "country": "United States",
        "industry": "Healthcare",
        "keywords": "Travel nurse, Contract-to-hire",
        "notes": "Hiring through vendors.",
    })
    assert created.status_code == 200
    lead_id = created.json()["id"]
    detail = client.get(f"/api/leads/{lead_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["company"] == "Preview Hospital"
    assert body["phone"] == "+1-512-555-0100"
    assert body["email"] == "priya@previewhospital.example"
    assert body["contact_name"] == "Priya Shah"
    assert "Austin" in body["region"]
    assert body["industry"] == "Healthcare"
    assert body["keywords"] == "Travel nurse, Contract-to-hire"
    assert body["notes"] == "Hiring through vendors."
    assert body["source_url"].startswith("https://")
    assert body["created_at"]
    assert body["score"] is None

    page = client.get(f"/leads?id={lead_id}")
    assert page.status_code == 200
    assert "lead-summary.js" in page.text
    script = client.get("/static/lead-summary.js")
    assert script.status_code == 200
    assert "Summary preview" in script.text
    assert "mailto:" in script.text
    assert "tel:" in script.text
    assert "Not listed" in script.text
    assert "overflow-wrap:anywhere" in client.get("/static/styles.css").text
    assert "word-break:break-all" in client.get("/static/styles.css").text
    preview = client.get("/static/lead-preview.js")
    assert preview.status_code == 200
    assert "Open full lead" in preview.text
    assert 'event.key === "Escape"' in preview.text
    assert "data-close" in preview.text
    assert "gestureOpensPreview" in preview.text
    assert 'data-preview-lead' in client.get("/static/pipeline-ui.js").text
    assert "lead-preview.js" in page.text
