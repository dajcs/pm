"""Tests for card comments and board activity log."""
import pytest
from conftest import auth_header, login


async def _setup_card(client, headers, title="Comment Test Card"):
    board = await client.get("/api/board", headers=headers)
    col_id = board.json()["columns"][0]["id"]
    resp = await client.post(
        "/api/board/cards",
        json={"column_id": col_id, "title": title, "details": ""},
        headers=headers,
    )
    return resp.json()["id"]


@pytest.mark.anyio
async def test_comments_empty_by_default(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _setup_card(client, h)
    resp = await client.get(f"/api/board/cards/{card_id}/comments", headers=h)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_add_comment(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _setup_card(client, h)
    resp = await client.post(
        f"/api/board/cards/{card_id}/comments",
        json={"text": "This is a comment"},
        headers=h,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] > 0
    assert data["text"] == "This is a comment"
    assert data["username"] == "user"
    assert "created_at" in data


@pytest.mark.anyio
async def test_comment_appears_in_get(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _setup_card(client, h)
    await client.post(f"/api/board/cards/{card_id}/comments", json={"text": "Hello world"}, headers=h)
    resp = await client.get(f"/api/board/cards/{card_id}/comments", headers=h)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["text"] == "Hello world"
    assert items[0]["username"] == "user"


@pytest.mark.anyio
async def test_multiple_comments_ordered(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _setup_card(client, h)
    for msg in ["first", "second", "third"]:
        await client.post(f"/api/board/cards/{card_id}/comments", json={"text": msg}, headers=h)
    resp = await client.get(f"/api/board/cards/{card_id}/comments", headers=h)
    texts = [c["text"] for c in resp.json()]
    assert texts == ["first", "second", "third"]


@pytest.mark.anyio
async def test_delete_own_comment(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _setup_card(client, h)
    add_resp = await client.post(
        f"/api/board/cards/{card_id}/comments", json={"text": "To be deleted"}, headers=h
    )
    comment_id = add_resp.json()["id"]
    del_resp = await client.delete(f"/api/board/cards/{card_id}/comments/{comment_id}", headers=h)
    assert del_resp.status_code == 200
    resp = await client.get(f"/api/board/cards/{card_id}/comments", headers=h)
    assert resp.json() == []


@pytest.mark.anyio
async def test_delete_other_users_comment_forbidden(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _setup_card(client, h)
    add_resp = await client.post(
        f"/api/board/cards/{card_id}/comments", json={"text": "User1 comment"}, headers=h
    )
    comment_id = add_resp.json()["id"]
    # Register second user with their own board
    reg = await client.post("/api/auth/register", json={"username": "commenter2", "password": "pass123"})
    token2 = reg.json()["token"]
    h2 = auth_header(token2)
    # user2 accesses their own board — card_id belongs to user1's board, not found
    del_resp = await client.delete(f"/api/board/cards/{card_id}/comments/{comment_id}", headers=h2)
    assert del_resp.status_code == 404


@pytest.mark.anyio
async def test_comment_count_in_board(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _setup_card(client, h)
    await client.post(f"/api/board/cards/{card_id}/comments", json={"text": "c1"}, headers=h)
    await client.post(f"/api/board/cards/{card_id}/comments", json={"text": "c2"}, headers=h)
    board = (await client.get("/api/board", headers=h)).json()
    assert board["cards"][card_id]["comment_count"] == 2


@pytest.mark.anyio
async def test_comment_deleted_with_card(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _setup_card(client, h)
    await client.post(f"/api/board/cards/{card_id}/comments", json={"text": "orphan"}, headers=h)
    await client.delete(f"/api/board/cards/{card_id}", headers=h)
    board = (await client.get("/api/board", headers=h)).json()
    assert card_id not in board["cards"]


@pytest.mark.anyio
async def test_comment_requires_auth(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _setup_card(client, h)
    resp = await client.get(f"/api/board/cards/{card_id}/comments")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_board_activity_log(client):
    token = await login(client)
    h = auth_header(token)
    board = (await client.get("/api/board", headers=h)).json()
    col_id = board["columns"][0]["id"]
    await client.post(
        "/api/board/cards",
        json={"column_id": col_id, "title": "Activity Card", "details": ""},
        headers=h,
    )
    boards = (await client.get("/api/boards", headers=h)).json()
    board_id = boards[0]["id"]
    resp = await client.get(f"/api/boards/{board_id}/activity", headers=h)
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) >= 1
    assert any("Activity Card" in e["action"] for e in entries)
    assert entries[0]["username"] == "user"


@pytest.mark.anyio
async def test_activity_requires_auth(client):
    token = await login(client)
    h = auth_header(token)
    # Trigger board creation first
    await client.get("/api/board", headers=h)
    boards = (await client.get("/api/boards", headers=h)).json()
    board_id = boards[0]["id"]
    resp = await client.get(f"/api/boards/{board_id}/activity")
    assert resp.status_code == 401
