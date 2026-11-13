"""Stand-ins used only by tests. The running app does not invent search results or model text."""


def install_fake_llm(monkeypatch):
    def complete_json(self, *, purpose, system, prompt):
        if purpose == "ai_search_plan":
            data = {
                "profile": "Hospitals that may buy radios",
                "locations": ["Gujarat"],
                "signals": ["walkie-talkies"],
                "queries": ["hospitals Gujarat radios", "hospital radio suppliers Gujarat", "Boondock Echo buyers"],
            }
        elif purpose == "ai_search_refine":
            data = {
                "queries": ["hospitals Gujarat official site", "radios Gujarat directory", "hospital procurement Gujarat"],
            }
        elif purpose == "ai_search_extract":
            data = {"companies": []}
        elif purpose == "company_research":
            data = {"summary": "Public notes describe an active team.", "signals": ["hiring"]}
        elif purpose == "lead_qualification":
            data = {"score": 72, "fit": "medium", "reasons": ["Has a contact email"], "recommend_qualify": True}
        elif purpose == "outreach_draft":
            data = {"subject": "A short introduction", "body": "This is a draft and has not been sent.\n\n" + prompt}
        else:
            raise AssertionError(purpose)
        return {"data": data, "provider": "openai", "model": "test", "note": ""}

    monkeypatch.setattr("app.providers.llm.LLMClient.complete_json", complete_json)


def install_fake_search(monkeypatch, rows):
    def choose(_db):
        return "tavily", "test-key"

    def search(_db, _criteria):
        return "tavily", "logistics companies", [dict(row) for row in rows]

    monkeypatch.setattr("app.search.providers.choose_search_provider", choose)
    monkeypatch.setattr("app.search.service.search_companies", search)
