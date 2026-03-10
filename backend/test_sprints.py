"""Tests for sprint management endpoints."""

import pytest
from httpx import AsyncClient

from conftest import auth_header, login


async def _setup(client: AsyncClient):
    """Login, initialize board, return (token, board_id, col_id)."""
    token = await login(client)
    h = auth_header(token)
    board_r = await client.get("/api/board", headers=h)
    boards = await client.get("/api/boards", headers=h)
    board_id = boards.json()[0]["id"]
    col_id = board_r.json()["columns"][0]["id"]
    return token, board_id, col_id


async def _make_card(client, token, board_id, col_id, title="Task"):
    r = await client.post(
        f"/api/board/cards?board_id={board_id}",
        json={"column_id": col_id, "title": title, "details": ""},
        headers=auth_header(token),
    )
    assert r.status_code == 201
    return r.json()["id"]


@pytest.mark.anyio
async def test_list_sprints_empty(client: AsyncClient):
    token, board_id, _ = await _setup(client)
    r = await client.get(f"/api/boards/{board_id}/sprints", headers=auth_header(token))
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.anyio
async def test_create_sprint(client: AsyncClient):
    token, board_id, _ = await _setup(client)
    r = await client.post(
        f"/api/boards/{board_id}/sprints",
        json={"name": "Sprint 1", "goal": "Ship v1", "start_date": "2026-03-01", "end_date": "2026-03-14"},
        headers=auth_header(token),
    )
    assert r.status_code == 201
    sprint = r.json()
    assert sprint["name"] == "Sprint 1"
    assert sprint["goal"] == "Ship v1"
    assert sprint["status"] == "planned"
    assert sprint["start_date"] == "2026-03-01"
    assert sprint["end_date"] == "2026-03-14"
    assert "id" in sprint


@pytest.mark.anyio
async def test_list_sprints(client: AsyncClient):
    token, board_id, _ = await _setup(client)
    h = auth_header(token)
    await client.post(f"/api/boards/{board_id}/sprints", json={"name": "Sprint A"}, headers=h)
    await client.post(f"/api/boards/{board_id}/sprints", json={"name": "Sprint B"}, headers=h)
    r = await client.get(f"/api/boards/{board_id}/sprints", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.anyio
async def test_get_sprint(client: AsyncClient):
    token, board_id, _ = await _setup(client)
    h = auth_header(token)
    cr = await client.post(f"/api/boards/{board_id}/sprints", json={"name": "Sprint 1"}, headers=h)
    sprint_id = cr.json()["id"]
    r = await client.get(f"/api/boards/{board_id}/sprints/{sprint_id}", headers=h)
    assert r.status_code == 200
    assert r.json()["name"] == "Sprint 1"
    assert "cards" in r.json()


@pytest.mark.anyio
async def test_update_sprint(client: AsyncClient):
    token, board_id, _ = await _setup(client)
    h = auth_header(token)
    cr = await client.post(f"/api/boards/{board_id}/sprints", json={"name": "Old Name"}, headers=h)
    sprint_id = cr.json()["id"]
    r = await client.patch(
        f"/api/boards/{board_id}/sprints/{sprint_id}",
        json={"name": "New Name", "status": "active"},
        headers=h,
    )
    assert r.status_code == 200
    gr = await client.get(f"/api/boards/{board_id}/sprints/{sprint_id}", headers=h)
    assert gr.json()["name"] == "New Name"
    assert gr.json()["status"] == "active"


@pytest.mark.anyio
async def test_delete_sprint(client: AsyncClient):
    token, board_id, _ = await _setup(client)
    h = auth_header(token)
    cr = await client.post(f"/api/boards/{board_id}/sprints", json={"name": "Sprint X"}, headers=h)
    sprint_id = cr.json()["id"]
    dr = await client.delete(f"/api/boards/{board_id}/sprints/{sprint_id}", headers=h)
    assert dr.status_code == 200
    lr = await client.get(f"/api/boards/{board_id}/sprints", headers=h)
    assert lr.json() == []


@pytest.mark.anyio
async def test_delete_nonexistent_sprint(client: AsyncClient):
    token, board_id, _ = await _setup(client)
    r = await client.delete(f"/api/boards/{board_id}/sprints/99999", headers=auth_header(token))
    assert r.status_code == 404


@pytest.mark.anyio
async def test_assign_card_to_sprint(client: AsyncClient):
    token, board_id, col_id = await _setup(client)
    h = auth_header(token)
    card_id = await _make_card(client, token, board_id, col_id)
    cr = await client.post(f"/api/boards/{board_id}/sprints", json={"name": "Sprint 1"}, headers=h)
    sprint_id = cr.json()["id"]

    r = await client.post(
        f"/api/board/cards/{card_id}/sprints?board_id={board_id}",
        json={"sprint_id": sprint_id},
        headers=h,
    )
    assert r.status_code == 200

    # Sprint should now have 1 card
    gr = await client.get(f"/api/boards/{board_id}/sprints/{sprint_id}", headers=h)
    assert len(gr.json()["cards"]) == 1
    assert gr.json()["cards"][0]["id"] == card_id


@pytest.mark.anyio
async def test_get_card_sprints(client: AsyncClient):
    token, board_id, col_id = await _setup(client)
    h = auth_header(token)
    card_id = await _make_card(client, token, board_id, col_id)
    cr = await client.post(f"/api/boards/{board_id}/sprints", json={"name": "Sprint 1"}, headers=h)
    sprint_id = cr.json()["id"]
    await client.post(
        f"/api/board/cards/{card_id}/sprints?board_id={board_id}",
        json={"sprint_id": sprint_id},
        headers=h,
    )
    r = await client.get(f"/api/board/cards/{card_id}/sprints?board_id={board_id}", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "Sprint 1"


@pytest.mark.anyio
async def test_remove_card_from_sprint(client: AsyncClient):
    token, board_id, col_id = await _setup(client)
    h = auth_header(token)
    card_id = await _make_card(client, token, board_id, col_id)
    cr = await client.post(f"/api/boards/{board_id}/sprints", json={"name": "Sprint 1"}, headers=h)
    sprint_id = cr.json()["id"]
    await client.post(
        f"/api/board/cards/{card_id}/sprints?board_id={board_id}",
        json={"sprint_id": sprint_id},
        headers=h,
    )
    dr = await client.delete(
        f"/api/board/cards/{card_id}/sprints/{sprint_id}?board_id={board_id}",
        headers=h,
    )
    assert dr.status_code == 200
    gr = await client.get(f"/api/boards/{board_id}/sprints/{sprint_id}", headers=h)
    assert gr.json()["cards"] == []


@pytest.mark.anyio
async def test_assign_duplicate_card_to_sprint(client: AsyncClient):
    token, board_id, col_id = await _setup(client)
    h = auth_header(token)
    card_id = await _make_card(client, token, board_id, col_id)
    cr = await client.post(f"/api/boards/{board_id}/sprints", json={"name": "Sprint 1"}, headers=h)
    sprint_id = cr.json()["id"]
    await client.post(
        f"/api/board/cards/{card_id}/sprints?board_id={board_id}",
        json={"sprint_id": sprint_id},
        headers=h,
    )
    r2 = await client.post(
        f"/api/board/cards/{card_id}/sprints?board_id={board_id}",
        json={"sprint_id": sprint_id},
        headers=h,
    )
    assert r2.status_code == 409


@pytest.mark.anyio
async def test_sprint_card_counts(client: AsyncClient):
    token, board_id, col_id = await _setup(client)
    h = auth_header(token)
    card_id1 = await _make_card(client, token, board_id, col_id, "Task 1")
    card_id2 = await _make_card(client, token, board_id, col_id, "Task 2")
    cr = await client.post(f"/api/boards/{board_id}/sprints", json={"name": "Sprint 1"}, headers=h)
    sprint_id = cr.json()["id"]
    await client.post(
        f"/api/board/cards/{card_id1}/sprints?board_id={board_id}",
        json={"sprint_id": sprint_id}, headers=h,
    )
    await client.post(
        f"/api/board/cards/{card_id2}/sprints?board_id={board_id}",
        json={"sprint_id": sprint_id}, headers=h,
    )
    lr = await client.get(f"/api/boards/{board_id}/sprints", headers=h)
    s = lr.json()[0]
    assert s["total_cards"] == 2
    assert s["done_cards"] == 0  # no cards in "Done" column


@pytest.mark.anyio
async def test_sprint_on_wrong_board(client: AsyncClient):
    token, board_id, _ = await _setup(client)
    h = auth_header(token)
    # Create second board
    b2 = await client.post("/api/boards", json={"name": "Board 2"}, headers=h)
    board2_id = b2.json()["id"]
    # Create sprint on board 1
    cr = await client.post(f"/api/boards/{board_id}/sprints", json={"name": "Sprint 1"}, headers=h)
    sprint_id = cr.json()["id"]
    # Accessing sprint on wrong board returns 404
    r = await client.get(f"/api/boards/{board2_id}/sprints/{sprint_id}", headers=h)
    assert r.status_code == 404


@pytest.mark.anyio
async def test_sprint_without_dates(client: AsyncClient):
    token, board_id, _ = await _setup(client)
    r = await client.post(
        f"/api/boards/{board_id}/sprints",
        json={"name": "Flexible Sprint"},
        headers=auth_header(token),
    )
    assert r.status_code == 201
    sprint = r.json()
    assert sprint["start_date"] is None
    assert sprint["end_date"] is None
