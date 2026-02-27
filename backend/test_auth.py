import pytest


@pytest.mark.anyio
async def test_login_success(client):
    res = await client.post("/api/auth/login", json={"username": "user", "password": "password"})
    assert res.status_code == 200
    data = res.json()
    assert "token" in data


@pytest.mark.anyio
async def test_login_wrong_password(client):
    res = await client.post("/api/auth/login", json={"username": "user", "password": "wrong"})
    assert res.status_code == 401


@pytest.mark.anyio
async def test_login_wrong_username(client):
    res = await client.post("/api/auth/login", json={"username": "nobody", "password": "password"})
    assert res.status_code == 401


@pytest.mark.anyio
async def test_me_valid_token(client):
    login = await client.post("/api/auth/login", json={"username": "user", "password": "password"})
    token = login.json()["token"]
    res = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json() == {"username": "user"}


@pytest.mark.anyio
async def test_me_no_token(client):
    res = await client.get("/api/auth/me")
    assert res.status_code == 401


@pytest.mark.anyio
async def test_me_bad_token(client):
    res = await client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"})
    assert res.status_code == 401
