"""Tests for card archiving and restoration."""
import pytest
from conftest import auth_header, login


async def _board_with_card(client, headers, title="Archive Me"):
    board_data = (await client.get("/api/board", headers=headers)).json()
    col_id = board_data["columns"][0]["id"]
    resp = await client.post(
        "/api/board/cards",
        json={"column_id": col_id, "title": title, "details": "d"},
        headers=headers,
    )
    return resp.json()["id"]


@pytest.mark.anyio
async def test_archive_card(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _board_with_card(client, h)
    resp = await client.post(f"/api/board/cards/{card_id}/archive", headers=h)
    assert resp.status_code == 200
    # Card should no longer be in board
    board = (await client.get("/api/board", headers=h)).json()
    assert card_id not in board["cards"]


@pytest.mark.anyio
async def test_archived_cards_listed(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _board_with_card(client, h, "To Archive")
    await client.post(f"/api/board/cards/{card_id}/archive", headers=h)
    resp = await client.get("/api/board/archived-cards", headers=h)
    assert resp.status_code == 200
    archived = resp.json()
    assert any(c["id"] == card_id for c in archived)
    card = next(c for c in archived if c["id"] == card_id)
    assert card["title"] == "To Archive"
    assert "column_title" in card


@pytest.mark.anyio
async def test_restore_card(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _board_with_card(client, h, "Restore Me")
    await client.post(f"/api/board/cards/{card_id}/archive", headers=h)
    # Restore
    resp = await client.post(f"/api/board/cards/{card_id}/restore", headers=h)
    assert resp.status_code == 200
    # Should be back in board
    board = (await client.get("/api/board", headers=h)).json()
    assert card_id in board["cards"]
    # Should not be in archived list
    archived = (await client.get("/api/board/archived-cards", headers=h)).json()
    assert not any(c["id"] == card_id for c in archived)


@pytest.mark.anyio
async def test_archive_not_found(client):
    token = await login(client)
    h = auth_header(token)
    await client.get("/api/board", headers=h)
    resp = await client.post("/api/board/cards/ghost-card/archive", headers=h)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_restore_not_found(client):
    token = await login(client)
    h = auth_header(token)
    await client.get("/api/board", headers=h)
    resp = await client.post("/api/board/cards/ghost-card/restore", headers=h)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_archived_card_not_in_board_load(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _board_with_card(client, h, "Hidden")
    await client.post(f"/api/board/cards/{card_id}/archive", headers=h)
    board = (await client.get("/api/board", headers=h)).json()
    for col in board["columns"]:
        assert card_id not in col["cardIds"]
    assert card_id not in board["cards"]


@pytest.mark.anyio
async def test_archived_empty_by_default(client):
    token = await login(client)
    h = auth_header(token)
    await client.get("/api/board", headers=h)
    resp = await client.get("/api/board/archived-cards", headers=h)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_archive_logs_activity(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _board_with_card(client, h, "Log This")
    await client.post(f"/api/board/cards/{card_id}/archive", headers=h)
    boards = (await client.get("/api/boards", headers=h)).json()
    board_id = boards[0]["id"]
    activity = (await client.get(f"/api/boards/{board_id}/activity", headers=h)).json()
    assert any("archived" in e["action"] for e in activity)


@pytest.mark.anyio
async def test_archive_requires_auth(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _board_with_card(client, h)
    resp = await client.post(f"/api/board/cards/{card_id}/archive")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_archived_card_isolation(client):
    """User2 cannot restore user1's archived card."""
    token = await login(client)
    h = auth_header(token)
    card_id = await _board_with_card(client, h, "User1 Card")
    await client.post(f"/api/board/cards/{card_id}/archive", headers=h)
    # Register user2
    reg = await client.post("/api/auth/register", json={"username": "archother", "password": "pass123"})
    h2 = auth_header(reg.json()["token"])
    resp = await client.post(f"/api/board/cards/{card_id}/restore", headers=h2)
    assert resp.status_code == 404
