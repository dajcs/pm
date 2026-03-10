import pytest
from conftest import auth_header, login


@pytest.mark.anyio
async def test_create_card_with_priority(client):
    token = await login(client)
    headers = auth_header(token)
    board_data = (await client.get("/api/board", headers=headers)).json()
    col_id = board_data["columns"][0]["id"]

    res = await client.post(
        "/api/board/cards",
        json={"column_id": col_id, "title": "High prio task", "priority": "high"},
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["priority"] == "high"

    board = await client.get("/api/board", headers=headers)
    card = board.json()["cards"][data["id"]]
    assert card["priority"] == "high"


@pytest.mark.anyio
async def test_create_card_with_due_date(client):
    token = await login(client)
    headers = auth_header(token)
    board_data = (await client.get("/api/board", headers=headers)).json()
    col_id = board_data["columns"][0]["id"]

    res = await client.post(
        "/api/board/cards",
        json={"column_id": col_id, "title": "Due soon", "due_date": "2030-12-31"},
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["due_date"] == "2030-12-31"

    board = await client.get("/api/board", headers=headers)
    card = board.json()["cards"][data["id"]]
    assert card["due_date"] == "2030-12-31"


@pytest.mark.anyio
async def test_update_card_priority(client):
    token = await login(client)
    headers = auth_header(token)

    board = {
        "columns": [{"id": "col-a", "title": "A", "cardIds": ["card-mp"]}],
        "cards": {"card-mp": {"id": "card-mp", "title": "Meta", "details": "d", "priority": "none"}},
    }
    await client.put("/api/board", json=board, headers=headers)

    res = await client.patch(
        "/api/board/cards/card-mp", json={"priority": "urgent"}, headers=headers
    )
    assert res.status_code == 200

    board_res = await client.get("/api/board", headers=headers)
    assert board_res.json()["cards"]["card-mp"]["priority"] == "urgent"


@pytest.mark.anyio
async def test_update_card_due_date(client):
    token = await login(client)
    headers = auth_header(token)

    board = {
        "columns": [{"id": "col-a", "title": "A", "cardIds": ["card-dd"]}],
        "cards": {"card-dd": {"id": "card-dd", "title": "Due", "details": "d"}},
    }
    await client.put("/api/board", json=board, headers=headers)

    res = await client.patch(
        "/api/board/cards/card-dd", json={"due_date": "2025-06-15"}, headers=headers
    )
    assert res.status_code == 200

    board_res = await client.get("/api/board", headers=headers)
    assert board_res.json()["cards"]["card-dd"]["due_date"] == "2025-06-15"


@pytest.mark.anyio
async def test_clear_card_due_date(client):
    token = await login(client)
    headers = auth_header(token)

    board = {
        "columns": [{"id": "col-a", "title": "A", "cardIds": ["card-clr"]}],
        "cards": {"card-clr": {"id": "card-clr", "title": "Clear", "details": "d", "due_date": "2025-01-01"}},
    }
    await client.put("/api/board", json=board, headers=headers)

    res = await client.patch(
        "/api/board/cards/card-clr", json={"due_date": None}, headers=headers
    )
    assert res.status_code == 200

    board_res = await client.get("/api/board", headers=headers)
    assert board_res.json()["cards"]["card-clr"]["due_date"] is None


@pytest.mark.anyio
async def test_board_stats(client):
    token = await login(client)
    headers = auth_header(token)

    # Set up board with some cards
    board = {
        "columns": [
            {"id": "col-a", "title": "Todo", "cardIds": ["c1", "c2"]},
            {"id": "col-b", "title": "Done", "cardIds": ["c3"]},
        ],
        "cards": {
            "c1": {"id": "c1", "title": "T1", "details": "d"},
            "c2": {"id": "c2", "title": "T2", "details": "d", "due_date": "2000-01-01"},
            "c3": {"id": "c3", "title": "T3", "details": "d"},
        },
    }
    await client.put("/api/board", json=board, headers=headers)

    boards = await client.get("/api/boards", headers=headers)
    board_id = boards.json()[0]["id"]

    res = await client.get(f"/api/boards/{board_id}/stats", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_cards"] == 3
    assert data["cards_by_column"]["Todo"] == 2
    assert data["cards_by_column"]["Done"] == 1
    assert data["overdue_count"] >= 1  # c2 has past due date


@pytest.mark.anyio
async def test_board_stats_requires_auth(client):
    res = await client.get("/api/boards/1/stats")
    assert res.status_code == 401


@pytest.mark.anyio
async def test_board_description(client):
    token = await login(client)
    headers = auth_header(token)

    await client.get("/api/board", headers=headers)
    boards = await client.get("/api/boards", headers=headers)
    board_id = boards.json()[0]["id"]

    res = await client.patch(
        f"/api/boards/{board_id}/description",
        json={"description": "Sprint 1 board for team Alpha"},
        headers=headers,
    )
    assert res.status_code == 200

    boards_res = await client.get("/api/boards", headers=headers)
    board = next(b for b in boards_res.json() if b["id"] == board_id)
    assert board["description"] == "Sprint 1 board for team Alpha"


@pytest.mark.anyio
async def test_board_stats_wrong_user(client):
    """Cannot get stats for another user's board."""
    # Register second user
    res = await client.post(
        "/api/auth/register",
        json={"username": "statsother", "password": "password123"},
    )
    other_token = res.json()["token"]
    other_headers = auth_header(other_token)
    await client.get("/api/board", headers=other_headers)
    other_boards = await client.get("/api/boards", headers=other_headers)
    other_board_id = other_boards.json()[0]["id"]

    # Try to get stats with original user
    token = await login(client)
    headers = auth_header(token)
    res = await client.get(f"/api/boards/{other_board_id}/stats", headers=headers)
    assert res.status_code == 404
