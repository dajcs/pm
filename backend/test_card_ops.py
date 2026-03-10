"""Tests for card duplication and other card operations."""
import pytest
from conftest import auth_header, login


async def _setup(client, headers):
    """Return (board_id, col_id, card_id) for convenience."""
    await client.get("/api/board", headers=headers)
    boards = (await client.get("/api/boards", headers=headers)).json()
    board_id = boards[0]["id"]
    board = (await client.get(f"/api/board?board_id={board_id}", headers=headers)).json()
    col_id = board["columns"][0]["id"]
    r = await client.post(
        f"/api/board/cards?board_id={board_id}",
        json={"column_id": col_id, "title": "Original", "details": "Detail text", "priority": "high"},
        headers=headers,
    )
    return board_id, col_id, r.json()["id"]


@pytest.mark.anyio
async def test_duplicate_card(client):
    token = await login(client)
    h = auth_header(token)
    board_id, col_id, card_id = await _setup(client, h)

    r = await client.post(
        f"/api/board/cards/{card_id}/duplicate?board_id={board_id}",
        headers=h,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["id"] != card_id
    assert data["title"] == "Original (copy)"
    assert data["details"] == "Detail text"
    assert data["priority"] == "high"


@pytest.mark.anyio
async def test_duplicate_card_appears_in_board(client):
    token = await login(client)
    h = auth_header(token)
    board_id, col_id, card_id = await _setup(client, h)

    dup = (await client.post(
        f"/api/board/cards/{card_id}/duplicate?board_id={board_id}", headers=h
    )).json()

    board = (await client.get(f"/api/board?board_id={board_id}", headers=h)).json()
    assert dup["id"] in board["cards"]
    # Should be in same column
    col = next(c for c in board["columns"] if c["id"] == col_id)
    assert dup["id"] in col["cardIds"]


@pytest.mark.anyio
async def test_duplicate_card_copies_labels(client):
    token = await login(client)
    h = auth_header(token)
    board_id, col_id, card_id = await _setup(client, h)
    await client.patch(
        f"/api/board/cards/{card_id}?board_id={board_id}",
        json={"labels": ["bug", "feature"]},
        headers=h,
    )

    dup = (await client.post(
        f"/api/board/cards/{card_id}/duplicate?board_id={board_id}", headers=h
    )).json()

    board = (await client.get(f"/api/board?board_id={board_id}", headers=h)).json()
    assert set(board["cards"][dup["id"]]["labels"]) == {"bug", "feature"}


@pytest.mark.anyio
async def test_duplicate_nonexistent_card(client):
    token = await login(client)
    h = auth_header(token)
    await client.get("/api/board", headers=h)
    boards = (await client.get("/api/boards", headers=h)).json()
    board_id = boards[0]["id"]

    r = await client.post(
        f"/api/board/cards/no-such-card/duplicate?board_id={board_id}", headers=h
    )
    assert r.status_code == 404


@pytest.mark.anyio
async def test_duplicate_wrong_user(client):
    h1 = (lambda t: {"Authorization": f"Bearer {t}"})(
        (await client.post("/api/auth/login", json={"username": "user", "password": "password"})).json()["token"]
    )
    await client.post("/api/auth/register", json={"username": "dupint", "password": "duppass1"})
    h2 = (lambda t: {"Authorization": f"Bearer {t}"})(
        (await client.post("/api/auth/login", json={"username": "dupint", "password": "duppass1"})).json()["token"]
    )

    board_id, col_id, card_id = await _setup(client, h1)
    r = await client.post(
        f"/api/board/cards/{card_id}/duplicate?board_id={board_id}", headers=h2
    )
    assert r.status_code in (403, 404)


@pytest.mark.anyio
async def test_duplicate_logs_activity(client):
    token = await login(client)
    h = auth_header(token)
    board_id, col_id, card_id = await _setup(client, h)

    await client.post(
        f"/api/board/cards/{card_id}/duplicate?board_id={board_id}", headers=h
    )

    activity = (await client.get(f"/api/boards/{board_id}/activity", headers=h)).json()
    assert any("duplicat" in e["action"].lower() for e in activity)
