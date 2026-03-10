"""Tests for card time tracking endpoints."""

import pytest
from httpx import AsyncClient

from conftest import auth_header, login


async def _setup(client: AsyncClient):
    """Login, create a board and card. Return (token, board_id, card_id)."""
    token = await login(client)
    h = auth_header(token)
    await client.get("/api/board", headers=h)
    boards = await client.get("/api/boards", headers=h)
    board_id = boards.json()[0]["id"]

    col_r = await client.get(f"/api/board?board_id={board_id}", headers=h)
    col_id = col_r.json()["columns"][0]["id"]

    card_r = await client.post(
        f"/api/board/cards?board_id={board_id}",
        json={"column_id": col_id, "title": "Tracked", "details": ""},
        headers=h,
    )
    assert card_r.status_code == 201
    card_id = card_r.json()["id"]
    return token, board_id, card_id


@pytest.mark.anyio
async def test_list_empty(client: AsyncClient):
    token, board_id, card_id = await _setup(client)
    r = await client.get(
        f"/api/board/cards/{card_id}/time?board_id={board_id}",
        headers=auth_header(token),
    )
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.anyio
async def test_add_and_list(client: AsyncClient):
    token, board_id, card_id = await _setup(client)
    h = auth_header(token)
    r = await client.post(
        f"/api/board/cards/{card_id}/time?board_id={board_id}",
        json={"hours": 2.5, "description": "Initial work", "date": "2026-03-10"},
        headers=h,
    )
    assert r.status_code == 201
    entry = r.json()
    assert entry["hours"] == 2.5
    assert entry["description"] == "Initial work"
    assert entry["date"] == "2026-03-10"
    assert "id" in entry
    assert entry["username"] == "user"

    r2 = await client.get(
        f"/api/board/cards/{card_id}/time?board_id={board_id}",
        headers=h,
    )
    assert r2.status_code == 200
    entries = r2.json()
    assert len(entries) == 1
    assert entries[0]["hours"] == 2.5


@pytest.mark.anyio
async def test_add_multiple_entries(client: AsyncClient):
    token, board_id, card_id = await _setup(client)
    h = auth_header(token)
    await client.post(
        f"/api/board/cards/{card_id}/time?board_id={board_id}",
        json={"hours": 1.0, "description": "Morning", "date": "2026-03-10"},
        headers=h,
    )
    await client.post(
        f"/api/board/cards/{card_id}/time?board_id={board_id}",
        json={"hours": 3.0, "description": "Afternoon", "date": "2026-03-10"},
        headers=h,
    )
    r = await client.get(
        f"/api/board/cards/{card_id}/time?board_id={board_id}",
        headers=h,
    )
    assert len(r.json()) == 2


@pytest.mark.anyio
async def test_delete_own_entry(client: AsyncClient):
    token, board_id, card_id = await _setup(client)
    h = auth_header(token)
    r = await client.post(
        f"/api/board/cards/{card_id}/time?board_id={board_id}",
        json={"hours": 1.0, "description": "", "date": "2026-03-10"},
        headers=h,
    )
    entry_id = r.json()["id"]
    del_r = await client.delete(
        f"/api/board/cards/{card_id}/time/{entry_id}?board_id={board_id}",
        headers=h,
    )
    assert del_r.status_code == 200
    list_r = await client.get(
        f"/api/board/cards/{card_id}/time?board_id={board_id}",
        headers=h,
    )
    assert list_r.json() == []


@pytest.mark.anyio
async def test_delete_others_entry_forbidden(client: AsyncClient):
    """User B cannot delete User A's time entry."""
    token_a, board_id, card_id = await _setup(client)
    h_a = auth_header(token_a)

    # Register user B and invite to board
    reg = await client.post("/api/auth/register", json={"username": "alice", "password": "password123"})
    assert reg.status_code in (200, 201)
    await client.post(f"/api/boards/{board_id}/invite", json={"username": "alice"}, headers=h_a)

    token_b_r = await client.post("/api/auth/login", json={"username": "alice", "password": "password123"})
    token_b = token_b_r.json()["token"]
    h_b = auth_header(token_b)

    # A logs time
    r = await client.post(
        f"/api/board/cards/{card_id}/time?board_id={board_id}",
        json={"hours": 1.0, "description": "", "date": "2026-03-10"},
        headers=h_a,
    )
    entry_id = r.json()["id"]

    # B tries to delete A's entry
    del_r = await client.delete(
        f"/api/board/cards/{card_id}/time/{entry_id}?board_id={board_id}",
        headers=h_b,
    )
    assert del_r.status_code == 403


@pytest.mark.anyio
async def test_add_invalid_hours_zero(client: AsyncClient):
    token, board_id, card_id = await _setup(client)
    r = await client.post(
        f"/api/board/cards/{card_id}/time?board_id={board_id}",
        json={"hours": 0, "description": "", "date": "2026-03-10"},
        headers=auth_header(token),
    )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_add_invalid_hours_too_large(client: AsyncClient):
    token, board_id, card_id = await _setup(client)
    r = await client.post(
        f"/api/board/cards/{card_id}/time?board_id={board_id}",
        json={"hours": 25, "description": "", "date": "2026-03-10"},
        headers=auth_header(token),
    )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_time_card_not_found(client: AsyncClient):
    token, board_id, _ = await _setup(client)
    r = await client.get(
        f"/api/board/cards/nonexistent/time?board_id={board_id}",
        headers=auth_header(token),
    )
    assert r.status_code == 404


@pytest.mark.anyio
async def test_time_report_empty(client: AsyncClient):
    token, board_id, _ = await _setup(client)
    r = await client.get(
        f"/api/boards/{board_id}/time-report",
        headers=auth_header(token),
    )
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.anyio
async def test_time_report_aggregated(client: AsyncClient):
    token, board_id, card_id = await _setup(client)
    h = auth_header(token)
    await client.post(
        f"/api/board/cards/{card_id}/time?board_id={board_id}",
        json={"hours": 2.0, "description": "Morning", "date": "2026-03-10"},
        headers=h,
    )
    await client.post(
        f"/api/board/cards/{card_id}/time?board_id={board_id}",
        json={"hours": 3.5, "description": "Afternoon", "date": "2026-03-10"},
        headers=h,
    )
    r = await client.get(f"/api/boards/{board_id}/time-report", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["total_hours"] == 5.5
    assert data[0]["username"] == "user"
    assert data[0]["card_title"] == "Tracked"


@pytest.mark.anyio
async def test_time_report_multiple_cards(client: AsyncClient):
    token, board_id, card_id = await _setup(client)
    h = auth_header(token)

    # Create second card
    col_r = await client.get(f"/api/board?board_id={board_id}", headers=h)
    col_id = col_r.json()["columns"][0]["id"]
    card2_r = await client.post(
        f"/api/board/cards?board_id={board_id}",
        json={"column_id": col_id, "title": "Card Two", "details": ""},
        headers=h,
    )
    card2_id = card2_r.json()["id"]

    await client.post(
        f"/api/board/cards/{card_id}/time?board_id={board_id}",
        json={"hours": 1.0, "description": "", "date": "2026-03-10"},
        headers=h,
    )
    await client.post(
        f"/api/board/cards/{card2_id}/time?board_id={board_id}",
        json={"hours": 4.0, "description": "", "date": "2026-03-10"},
        headers=h,
    )
    r = await client.get(f"/api/boards/{board_id}/time-report", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 2
    # Sorted by total_hours DESC: card2 (4.0) first
    assert r.json()[0]["total_hours"] == 4.0


@pytest.mark.anyio
async def test_delete_nonexistent_entry(client: AsyncClient):
    token, board_id, card_id = await _setup(client)
    r = await client.delete(
        f"/api/board/cards/{card_id}/time/99999?board_id={board_id}",
        headers=auth_header(token),
    )
    assert r.status_code == 404


@pytest.mark.anyio
async def test_entry_without_description(client: AsyncClient):
    token, board_id, card_id = await _setup(client)
    r = await client.post(
        f"/api/board/cards/{card_id}/time?board_id={board_id}",
        json={"hours": 0.5, "date": "2026-03-10"},
        headers=auth_header(token),
    )
    assert r.status_code == 201
    assert r.json()["description"] == ""
