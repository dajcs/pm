import pytest
from conftest import auth_header, login


@pytest.mark.anyio
async def test_register_new_user(client):
    res = await client.post(
        "/api/auth/register",
        json={"username": "newuser", "password": "secure123"},
    )
    assert res.status_code == 201
    data = res.json()
    assert "token" in data


@pytest.mark.anyio
async def test_register_duplicate_username(client):
    await client.post(
        "/api/auth/register",
        json={"username": "dupuser", "password": "secure123"},
    )
    res = await client.post(
        "/api/auth/register",
        json={"username": "dupuser", "password": "different456"},
    )
    assert res.status_code == 409


@pytest.mark.anyio
async def test_register_and_login(client):
    await client.post(
        "/api/auth/register",
        json={"username": "reglogin", "password": "mypassword"},
    )
    res = await client.post(
        "/api/auth/login",
        json={"username": "reglogin", "password": "mypassword"},
    )
    assert res.status_code == 200
    assert "token" in res.json()


@pytest.mark.anyio
async def test_register_short_username(client):
    res = await client.post(
        "/api/auth/register",
        json={"username": "ab", "password": "secure123"},
    )
    assert res.status_code == 422


@pytest.mark.anyio
async def test_register_short_password(client):
    res = await client.post(
        "/api/auth/register",
        json={"username": "validuser", "password": "12345"},
    )
    assert res.status_code == 422


@pytest.mark.anyio
async def test_change_password(client):
    token = await login(client)
    headers = auth_header(token)

    res = await client.post(
        "/api/auth/change-password",
        json={"current_password": "password", "new_password": "newpassword123"},
        headers=headers,
    )
    assert res.status_code == 200

    # Login with new password
    login_res = await client.post(
        "/api/auth/login",
        json={"username": "user", "password": "newpassword123"},
    )
    assert login_res.status_code == 200


@pytest.mark.anyio
async def test_change_password_wrong_current(client):
    token = await login(client)
    headers = auth_header(token)

    res = await client.post(
        "/api/auth/change-password",
        json={"current_password": "wrongpassword", "new_password": "newpassword123"},
        headers=headers,
    )
    assert res.status_code == 401


@pytest.mark.anyio
async def test_new_user_gets_own_board(client):
    """Registered users get their own isolated board."""
    res = await client.post(
        "/api/auth/register",
        json={"username": "boarduser", "password": "secure123"},
    )
    token = res.json()["token"]
    headers = auth_header(token)

    board_res = await client.get("/api/board", headers=headers)
    assert board_res.status_code == 200
    assert len(board_res.json()["columns"]) == 5
