"""Tests for notifications system."""

import pytest
from httpx import AsyncClient

from conftest import auth_header, login


async def _register_login(client: AsyncClient, username: str, password: str = "password123") -> str:
    reg = await client.post("/api/auth/register", json={"username": username, "password": password})
    assert reg.status_code in (200, 201)
    login_r = await client.post("/api/auth/login", json={"username": username, "password": password})
    return login_r.json()["token"]


async def _setup_shared_board(client: AsyncClient):
    """Login as default user, create a board, register alice, invite alice.
    Return (token_owner, token_alice, board_id, col_id)."""
    token = await login(client)
    h = auth_header(token)
    await client.get("/api/board", headers=h)
    boards = await client.get("/api/boards", headers=h)
    board_id = boards.json()[0]["id"]
    board_r = await client.get(f"/api/board?board_id={board_id}", headers=h)
    col_id = board_r.json()["columns"][0]["id"]

    token_alice = await _register_login(client, "alice_notif")
    await client.post(f"/api/boards/{board_id}/invite", json={"username": "alice_notif"}, headers=h)
    return token, token_alice, board_id, col_id


@pytest.mark.anyio
async def test_initial_no_notifications(client: AsyncClient):
    token = await login(client)
    r = await client.get("/api/notifications", headers=auth_header(token))
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.anyio
async def test_unread_count_zero(client: AsyncClient):
    token = await login(client)
    r = await client.get("/api/notifications/count", headers=auth_header(token))
    assert r.status_code == 200
    assert r.json()["unread"] == 0


@pytest.mark.anyio
async def test_assignment_notification(client: AsyncClient):
    """Assigning a card to alice sends alice a notification."""
    token_owner, token_alice, board_id, col_id = await _setup_shared_board(client)

    # Create a card
    card_r = await client.post(
        f"/api/board/cards?board_id={board_id}",
        json={"column_id": col_id, "title": "Assigned Task", "details": ""},
        headers=auth_header(token_owner),
    )
    card_id = card_r.json()["id"]

    # Assign to alice
    await client.patch(
        f"/api/board/cards/{card_id}?board_id={board_id}",
        json={"assigned_to": "alice_notif"},
        headers=auth_header(token_owner),
    )

    # Alice should have a notification
    r = await client.get("/api/notifications", headers=auth_header(token_alice))
    assert r.status_code == 200
    notifs = r.json()
    assert len(notifs) >= 1
    assert any(n["type"] == "assignment" for n in notifs)
    assert any("assigned" in n["message"] for n in notifs)
    assert notifs[0]["read"] is False


@pytest.mark.anyio
async def test_no_self_assignment_notification(client: AsyncClient):
    """Assigning to yourself does not create a notification."""
    token = await login(client)
    h = auth_header(token)
    await client.get("/api/board", headers=h)
    boards = await client.get("/api/boards", headers=h)
    board_id = boards.json()[0]["id"]
    board_r = await client.get(f"/api/board?board_id={board_id}", headers=h)
    col_id = board_r.json()["columns"][0]["id"]
    card_r = await client.post(
        f"/api/board/cards?board_id={board_id}",
        json={"column_id": col_id, "title": "Self Assign", "details": ""},
        headers=h,
    )
    card_id = card_r.json()["id"]
    await client.patch(
        f"/api/board/cards/{card_id}?board_id={board_id}",
        json={"assigned_to": "user"},
        headers=h,
    )
    r = await client.get("/api/notifications", headers=h)
    assert r.json() == []


@pytest.mark.anyio
async def test_mention_notification(client: AsyncClient):
    """Mentioning @alice in a comment sends alice a notification."""
    token_owner, token_alice, board_id, col_id = await _setup_shared_board(client)
    card_r = await client.post(
        f"/api/board/cards?board_id={board_id}",
        json={"column_id": col_id, "title": "Discussion", "details": ""},
        headers=auth_header(token_owner),
    )
    card_id = card_r.json()["id"]

    # Comment with @mention
    await client.post(
        f"/api/board/cards/{card_id}/comments?board_id={board_id}",
        json={"text": "Hey @alice_notif please review this"},
        headers=auth_header(token_owner),
    )
    r = await client.get("/api/notifications", headers=auth_header(token_alice))
    notifs = r.json()
    assert any(n["type"] == "mention" for n in notifs)
    assert any("mentioned" in n["message"] for n in notifs)


@pytest.mark.anyio
async def test_no_self_mention_notification(client: AsyncClient):
    """Self-mention in comment does not create a notification."""
    token = await login(client)
    h = auth_header(token)
    await client.get("/api/board", headers=h)
    boards = await client.get("/api/boards", headers=h)
    board_id = boards.json()[0]["id"]
    board_r = await client.get(f"/api/board?board_id={board_id}", headers=h)
    col_id = board_r.json()["columns"][0]["id"]
    card_r = await client.post(
        f"/api/board/cards?board_id={board_id}",
        json={"column_id": col_id, "title": "Note", "details": ""},
        headers=h,
    )
    await client.post(
        f"/api/board/cards/{card_r.json()['id']}/comments?board_id={board_id}",
        json={"text": "reminder to @user self"},
        headers=h,
    )
    r = await client.get("/api/notifications", headers=h)
    assert r.json() == []


@pytest.mark.anyio
async def test_mark_all_read(client: AsyncClient):
    token_owner, token_alice, board_id, col_id = await _setup_shared_board(client)
    card_r = await client.post(
        f"/api/board/cards?board_id={board_id}",
        json={"column_id": col_id, "title": "Task", "details": ""},
        headers=auth_header(token_owner),
    )
    card_id = card_r.json()["id"]
    await client.patch(
        f"/api/board/cards/{card_id}?board_id={board_id}",
        json={"assigned_to": "alice_notif"},
        headers=auth_header(token_owner),
    )
    h_alice = auth_header(token_alice)
    count_r = await client.get("/api/notifications/count", headers=h_alice)
    assert count_r.json()["unread"] >= 1

    # Mark all read
    mr = await client.post("/api/notifications/read", json={}, headers=h_alice)
    assert mr.status_code == 200
    assert mr.json()["marked"] >= 1

    count_r2 = await client.get("/api/notifications/count", headers=h_alice)
    assert count_r2.json()["unread"] == 0


@pytest.mark.anyio
async def test_mark_specific_read(client: AsyncClient):
    token_owner, token_alice, board_id, col_id = await _setup_shared_board(client)
    card_r = await client.post(
        f"/api/board/cards?board_id={board_id}",
        json={"column_id": col_id, "title": "Task", "details": ""},
        headers=auth_header(token_owner),
    )
    card_id = card_r.json()["id"]
    await client.patch(
        f"/api/board/cards/{card_id}?board_id={board_id}",
        json={"assigned_to": "alice_notif"},
        headers=auth_header(token_owner),
    )
    h_alice = auth_header(token_alice)
    notifs = (await client.get("/api/notifications", headers=h_alice)).json()
    notif_id = notifs[0]["id"]

    mr = await client.post("/api/notifications/read", json={"ids": [notif_id]}, headers=h_alice)
    assert mr.status_code == 200
    notifs2 = (await client.get("/api/notifications", headers=h_alice)).json()
    assert all(n["read"] for n in notifs2 if n["id"] == notif_id)


@pytest.mark.anyio
async def test_delete_notification(client: AsyncClient):
    token_owner, token_alice, board_id, col_id = await _setup_shared_board(client)
    card_r = await client.post(
        f"/api/board/cards?board_id={board_id}",
        json={"column_id": col_id, "title": "Task", "details": ""},
        headers=auth_header(token_owner),
    )
    card_id = card_r.json()["id"]
    await client.patch(
        f"/api/board/cards/{card_id}?board_id={board_id}",
        json={"assigned_to": "alice_notif"},
        headers=auth_header(token_owner),
    )
    h_alice = auth_header(token_alice)
    notifs = (await client.get("/api/notifications", headers=h_alice)).json()
    notif_id = notifs[0]["id"]

    dr = await client.delete(f"/api/notifications/{notif_id}", headers=h_alice)
    assert dr.status_code == 200
    notifs2 = (await client.get("/api/notifications", headers=h_alice)).json()
    assert not any(n["id"] == notif_id for n in notifs2)


@pytest.mark.anyio
async def test_delete_others_notification_fails(client: AsyncClient):
    """Owner cannot delete alice's notification."""
    token_owner, token_alice, board_id, col_id = await _setup_shared_board(client)
    card_r = await client.post(
        f"/api/board/cards?board_id={board_id}",
        json={"column_id": col_id, "title": "Task", "details": ""},
        headers=auth_header(token_owner),
    )
    card_id = card_r.json()["id"]
    await client.patch(
        f"/api/board/cards/{card_id}?board_id={board_id}",
        json={"assigned_to": "alice_notif"},
        headers=auth_header(token_owner),
    )
    notifs = (await client.get("/api/notifications", headers=auth_header(token_alice))).json()
    notif_id = notifs[0]["id"]

    dr = await client.delete(f"/api/notifications/{notif_id}", headers=auth_header(token_owner))
    assert dr.status_code == 404


@pytest.mark.anyio
async def test_unread_only_filter(client: AsyncClient):
    token_owner, token_alice, board_id, col_id = await _setup_shared_board(client)
    card_r = await client.post(
        f"/api/board/cards?board_id={board_id}",
        json={"column_id": col_id, "title": "Task", "details": ""},
        headers=auth_header(token_owner),
    )
    card_id = card_r.json()["id"]
    await client.patch(
        f"/api/board/cards/{card_id}?board_id={board_id}",
        json={"assigned_to": "alice_notif"},
        headers=auth_header(token_owner),
    )
    h_alice = auth_header(token_alice)
    await client.post("/api/notifications/read", json={}, headers=h_alice)

    all_r = await client.get("/api/notifications", headers=h_alice)
    unread_r = await client.get("/api/notifications?unread_only=true", headers=h_alice)
    assert len(all_r.json()) >= 1
    assert unread_r.json() == []


@pytest.mark.anyio
async def test_board_id_in_notification(client: AsyncClient):
    """Notification includes board_id so frontend can navigate."""
    token_owner, token_alice, board_id, col_id = await _setup_shared_board(client)
    card_r = await client.post(
        f"/api/board/cards?board_id={board_id}",
        json={"column_id": col_id, "title": "Task", "details": ""},
        headers=auth_header(token_owner),
    )
    card_id = card_r.json()["id"]
    await client.patch(
        f"/api/board/cards/{card_id}?board_id={board_id}",
        json={"assigned_to": "alice_notif"},
        headers=auth_header(token_owner),
    )
    notifs = (await client.get("/api/notifications", headers=auth_header(token_alice))).json()
    assert notifs[0]["board_id"] == board_id
    assert notifs[0]["card_id"] == card_id
