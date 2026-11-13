def login(client, email, name="Test User"):
    return client.post("/auth/demo/login", json={"email": email, "name": name})
