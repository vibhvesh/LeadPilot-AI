from tests.helpers import login


def test_health_is_public(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_workspace_requires_sign_in(client):
    assert client.get("/api/me").status_code == 401
    page = client.get("/", follow_redirects=False)
    assert page.status_code == 302
    assert page.headers["location"] == "/login"


def test_super_admin_demo_login_and_logout(client):
    response = login(client, "vibhvesh@gmail.com", "Vibhvesh")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["user"]["role"] == "super_admin"
    me = client.get("/api/me")
    assert me.status_code == 200
    assert me.json()["email"] == "vibhvesh@gmail.com"
    assert "leads" in me.json()["permissions"]
    client.post("/auth/logout")
    assert client.get("/api/me").status_code == 401


def test_new_user_is_pending_until_approved(client):
    pending = login(client, "new.user@example.com", "New User")
    assert pending.json()["status"] == "pending"
    assert client.get("/api/leads").status_code == 401

    admin = login(client, "vibhvesh@gmail.com", "Vibhvesh")
    assert admin.json()["status"] == "approved"
    users = client.get("/api/users").json()["users"]
    newbie = next(user for user in users if user["email"] == "new.user@example.com")
    assert newbie["status"] == "pending"
    decision = client.post(f"/api/users/{newbie['id']}/decision", json={"decision": "approve"})
    assert decision.status_code == 200
    assert decision.json()["status"] == "approved"
    client.post("/auth/logout")

    approved = login(client, "new.user@example.com", "New User")
    assert approved.json()["status"] == "approved"
    assert approved.json()["user"]["role"] == "member"
    assert client.get("/api/leads").status_code == 200
    assert client.get("/api/users").status_code == 403
    assert client.get("/api/providers").status_code == 403


def test_rejected_user_cannot_sign_in(client):
    login(client, "blocked@example.com", "Blocked")
    login(client, "vibhvesh@gmail.com", "Vibhvesh")
    users = client.get("/api/users").json()["users"]
    blocked = next(user for user in users if user["email"] == "blocked@example.com")
    client.post(f"/api/users/{blocked['id']}/decision", json={"decision": "reject"})
    client.post("/auth/logout")
    response = login(client, "blocked@example.com", "Blocked")
    assert response.status_code == 403


def test_user_permission_override_is_enforced(client):
    login(client, "member@example.com", "Member")
    login(client, "vibhvesh@gmail.com", "Vibhvesh")
    users = client.get("/api/users").json()["users"]
    member = next(user for user in users if user["email"] == "member@example.com")
    client.post(f"/api/users/{member['id']}/decision", json={"decision": "approve"})
    override = {module: {"view": module == "dashboard", "manage": False} for module in client.get("/api/me").json()["permissions"]}
    saved = client.put(f"/api/users/{member['id']}/permissions", json={"permissions": override})
    assert saved.status_code == 200
    client.post("/auth/logout")
    login(client, "member@example.com", "Member")
    assert client.get("/api/dashboard").status_code == 200
    assert client.get("/api/leads").status_code == 403
    assert client.post("/api/leads", json={"company": "Should Fail"}).status_code == 403


def test_only_super_admin_edits_role_templates(client):
    login(client, "admin@example.com", "Admin")
    login(client, "vibhvesh@gmail.com", "Vibhvesh")
    users = client.get("/api/users").json()["users"]
    admin = next(user for user in users if user["email"] == "admin@example.com")
    client.post(f"/api/users/{admin['id']}/decision", json={"decision": "approve"})
    client.patch(f"/api/users/{admin['id']}", json={"role": "admin"})
    client.post("/auth/logout")
    login(client, "admin@example.com", "Admin")
    response = client.put("/api/permissions/roles/member", json={"permissions": {}})
    assert response.status_code == 403


def test_login_page_renders(client):
    page = client.get("/login")
    assert page.status_code == 200
    assert "Sign in" in page.text
    login(client, "vibhvesh@gmail.com", "Vibhvesh")
    home = client.get("/")
    assert "GrokBot" in home.text
    assert "Search criteria" in home.text
