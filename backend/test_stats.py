"""Tests for enhanced board stats and bulk archive endpoints."""

import pytest
from conftest import auth_header, login


async def _register_and_login(client, username, password):
    await client.post("/api/auth/register", json={"username": username, "password": password})
    r = await client.post("/api/auth/login", json={"username": username, "password": password})
    return auth_header(r.json()["token"])


async def _get_board_and_col(client, headers):
    """Return (board_id, first_col_id) for the user's default board."""
    # Trigger lazy board creation, then get board_id from boards list
    await client.get("/api/board", headers=headers)
    boards = (await client.get("/api/boards", headers=headers)).json()
    board_id = boards[0]["id"]
    board = (await client.get(f"/api/board?board_id={board_id}", headers=headers)).json()
    col_id = board["columns"][0]["id"]
    return board_id, col_id


async def _create_card(client, headers, board_id, col_id, title="Card", priority="none"):
    r = await client.post(
        f"/api/board/cards?board_id={board_id}",
        json={"column_id": col_id, "title": title, "details": "d", "priority": priority},
        headers=headers,
    )
    return r.json()["id"]


@pytest.mark.anyio
async def test_stats_has_all_fields(client):
    token = await login(client)
    h = auth_header(token)
    await client.get("/api/board", headers=h)  # trigger board creation
    boards = (await client.get("/api/boards", headers=h)).json()
    board_id = boards[0]["id"]

    r = await client.get(f"/api/boards/{board_id}/stats", headers=h)
    assert r.status_code == 200
    data = r.json()
    for field in ("total_cards", "cards_by_column", "overdue_count",
                  "cards_by_priority", "due_soon_count", "assigned_count", "unassigned_count"):
        assert field in data, f"Missing field: {field}"


@pytest.mark.anyio
async def test_stats_excludes_archived(client):
    """Archived cards must not appear in stats totals."""
    token = await login(client)
    h = auth_header(token)
    board_id, col_id = await _get_board_and_col(client, h)

    ids = [await _create_card(client, h, board_id, col_id, f"C{i}") for i in range(3)]
    # Archive one
    await client.post(f"/api/board/cards/{ids[0]}/archive?board_id={board_id}", headers=h)

    data = (await client.get(f"/api/boards/{board_id}/stats", headers=h)).json()
    assert data["total_cards"] == 2
    assert data["unassigned_count"] == 2


@pytest.mark.anyio
async def test_stats_priority_breakdown(client):
    token = await login(client)
    h = auth_header(token)
    board_id, col_id = await _get_board_and_col(client, h)

    for p in ["high", "high", "low", "none"]:
        await _create_card(client, h, board_id, col_id, priority=p)

    data = (await client.get(f"/api/boards/{board_id}/stats", headers=h)).json()
    by_prio = data["cards_by_priority"]
    assert by_prio.get("high", 0) == 2
    assert by_prio.get("low", 0) == 1
    assert by_prio.get("none", 0) == 1


@pytest.mark.anyio
async def test_stats_assigned_count(client):
    token = await login(client)
    h = auth_header(token)
    board_id, col_id = await _get_board_and_col(client, h)

    ids = [await _create_card(client, h, board_id, col_id, f"C{i}") for i in range(3)]
    # Assign 2
    for cid in ids[:2]:
        await client.patch(
            f"/api/board/cards/{cid}?board_id={board_id}",
            json={"assigned_to": "user"},
            headers=h,
        )

    data = (await client.get(f"/api/boards/{board_id}/stats", headers=h)).json()
    assert data["assigned_count"] == 2
    assert data["unassigned_count"] == 1


@pytest.mark.anyio
async def test_stats_wrong_user_forbidden(client):
    h1 = await _register_and_login(client, "statsown", "statspass1")
    h2 = await _register_and_login(client, "statsint", "statspass2")

    await client.get("/api/board", headers=h1)  # trigger board creation
    boards = (await client.get("/api/boards", headers=h1)).json()
    board_id = boards[0]["id"]

    # Returns 404 to avoid leaking board existence to unauthorized users
    r = await client.get(f"/api/boards/{board_id}/stats", headers=h2)
    assert r.status_code in (403, 404)


@pytest.mark.anyio
async def test_bulk_archive_column(client):
    token = await login(client)
    h = auth_header(token)
    board_id, col_id = await _get_board_and_col(client, h)

    for i in range(4):
        await _create_card(client, h, board_id, col_id, f"Bulk {i}")

    r = await client.post(
        f"/api/board/columns/{col_id}/archive-all?board_id={board_id}", headers=h
    )
    assert r.status_code == 200
    assert r.json()["archived_count"] == 4

    board = (await client.get(f"/api/board?board_id={board_id}", headers=h)).json()
    col_cards = next((c["cardIds"] for c in board["columns"] if c["id"] == col_id), [])
    assert col_cards == []


@pytest.mark.anyio
async def test_bulk_archive_empty_column(client):
    token = await login(client)
    h = auth_header(token)
    board_id, col_id = await _get_board_and_col(client, h)

    r = await client.post(
        f"/api/board/columns/{col_id}/archive-all?board_id={board_id}", headers=h
    )
    assert r.status_code == 200
    assert r.json()["archived_count"] == 0


@pytest.mark.anyio
async def test_bulk_archive_skips_already_archived(client):
    """Bulk archive should only affect non-archived cards."""
    token = await login(client)
    h = auth_header(token)
    board_id, col_id = await _get_board_and_col(client, h)

    ids = [await _create_card(client, h, board_id, col_id, f"C{i}") for i in range(3)]
    # Manually archive one first
    await client.post(f"/api/board/cards/{ids[0]}/archive?board_id={board_id}", headers=h)

    r = await client.post(
        f"/api/board/columns/{col_id}/archive-all?board_id={board_id}", headers=h
    )
    assert r.json()["archived_count"] == 2


@pytest.mark.anyio
async def test_bulk_archive_wrong_user(client):
    h1 = await _register_and_login(client, "bulkown2", "bulkpass10")
    h2 = await _register_and_login(client, "bulkint2", "bulkpass11")

    board_id, col_id = await _get_board_and_col(client, h1)

    r = await client.post(
        f"/api/board/columns/{col_id}/archive-all?board_id={board_id}", headers=h2
    )
    assert r.status_code in (403, 404)


@pytest.mark.anyio
async def test_bulk_archive_logs_activity(client):
    token = await login(client)
    h = auth_header(token)
    board_id, col_id = await _get_board_and_col(client, h)

    await _create_card(client, h, board_id, col_id, "Activity Card")
    await client.post(
        f"/api/board/columns/{col_id}/archive-all?board_id={board_id}", headers=h
    )

    activity = (await client.get(f"/api/boards/{board_id}/activity", headers=h)).json()
    assert any("archived" in e["action"] for e in activity)
