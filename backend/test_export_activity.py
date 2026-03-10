"""Tests for board export and custom activity logging."""
import pytest
from conftest import auth_header, login


@pytest.mark.anyio
async def test_export_board_structure(client):
    token = await login(client)
    h = auth_header(token)
    # Set up board with a card
    board = {
        "columns": [{"id": "col-a", "title": "Todo", "cardIds": ["c1"]}],
        "cards": {"c1": {"id": "c1", "title": "Export me", "details": "d"}},
    }
    await client.put("/api/board", json=board, headers=h)
    boards = (await client.get("/api/boards", headers=h)).json()
    bid = boards[0]["id"]

    resp = await client.get(f"/api/boards/{bid}/export", headers=h)
    assert resp.status_code == 200
    data = resp.json()
    assert "board" in data
    assert "columns" in data
    assert "cards" in data
    assert "exported_at" in data
    assert data["board"]["name"] is not None


@pytest.mark.anyio
async def test_export_includes_archived(client):
    token = await login(client)
    h = auth_header(token)
    board_data = (await client.get("/api/board", headers=h)).json()
    col_id = board_data["columns"][0]["id"]
    card_resp = await client.post(
        "/api/board/cards",
        json={"column_id": col_id, "title": "Archived card", "details": "d"},
        headers=h,
    )
    card_id = card_resp.json()["id"]
    await client.post(f"/api/board/cards/{card_id}/archive", headers=h)

    boards = (await client.get("/api/boards", headers=h)).json()
    bid = boards[0]["id"]
    data = (await client.get(f"/api/boards/{bid}/export", headers=h)).json()
    card_ids = [c["id"] for c in data["cards"]]
    assert card_id in card_ids
    archived_card = next(c for c in data["cards"] if c["id"] == card_id)
    assert archived_card["archived"] is True


@pytest.mark.anyio
async def test_export_requires_auth(client):
    token = await login(client)
    h = auth_header(token)
    await client.get("/api/board", headers=h)
    boards = (await client.get("/api/boards", headers=h)).json()
    bid = boards[0]["id"]
    resp = await client.get(f"/api/boards/{bid}/export")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_export_wrong_user(client):
    token = await login(client)
    h = auth_header(token)
    await client.get("/api/board", headers=h)
    boards = (await client.get("/api/boards", headers=h)).json()
    bid = boards[0]["id"]

    reg = await client.post("/api/auth/register", json={"username": "exporter2", "password": "pass123"})
    h2 = auth_header(reg.json()["token"])
    resp = await client.get(f"/api/boards/{bid}/export", headers=h2)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_log_custom_activity(client):
    token = await login(client)
    h = auth_header(token)
    await client.get("/api/board", headers=h)
    boards = (await client.get("/api/boards", headers=h)).json()
    bid = boards[0]["id"]

    resp = await client.post(
        f"/api/boards/{bid}/activity",
        json={"action": "moved card 'Fix bug' from Backlog to In Progress"},
        headers=h,
    )
    assert resp.status_code == 200

    activity = (await client.get(f"/api/boards/{bid}/activity", headers=h)).json()
    assert any("moved card" in e["action"] for e in activity)


@pytest.mark.anyio
async def test_log_activity_requires_auth(client):
    token = await login(client)
    h = auth_header(token)
    await client.get("/api/board", headers=h)
    boards = (await client.get("/api/boards", headers=h)).json()
    bid = boards[0]["id"]

    resp = await client.post(f"/api/boards/{bid}/activity", json={"action": "test"})
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_log_activity_wrong_user(client):
    token = await login(client)
    h = auth_header(token)
    await client.get("/api/board", headers=h)
    boards = (await client.get("/api/boards", headers=h)).json()
    bid = boards[0]["id"]

    reg = await client.post("/api/auth/register", json={"username": "actother", "password": "pass123"})
    h2 = auth_header(reg.json()["token"])
    resp = await client.post(f"/api/boards/{bid}/activity", json={"action": "test"}, headers=h2)
    assert resp.status_code == 404
