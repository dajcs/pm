import pytest

import database
from conftest import auth_header, login


@pytest.mark.anyio
async def test_init_db_creates_tables(client):
    db = await database.get_db()
    try:
        tables = await db.execute_fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        names = [r["name"] for r in tables]
        assert "users" in names
        assert "boards" in names
        assert "columns" in names
        assert "cards" in names
    finally:
        await db.close()


@pytest.mark.anyio
async def test_init_db_seeds_user(client):
    user = await database.get_user_by_username("user")
    assert user is not None
    assert user["username"] == "user"
    assert database.verify_password("password", user["password_hash"])


@pytest.mark.anyio
async def test_get_board_creates_default(client):
    token = await login(client)
    res = await client.get("/api/board", headers=auth_header(token))
    assert res.status_code == 200
    data = res.json()
    assert len(data["columns"]) == 5
    assert data["columns"][0]["id"] == "col-backlog"
    assert data["cards"] == {}


@pytest.mark.anyio
async def test_get_board_requires_auth(client):
    res = await client.get("/api/board")
    assert res.status_code == 401


@pytest.mark.anyio
async def test_put_board(client):
    token = await login(client)
    headers = auth_header(token)

    board = {
        "columns": [
            {"id": "col-a", "title": "Alpha", "cardIds": ["card-1"]},
            {"id": "col-b", "title": "Beta", "cardIds": []},
        ],
        "cards": {
            "card-1": {"id": "card-1", "title": "Test Card", "details": "Some details"},
        },
    }
    res = await client.put("/api/board", json=board, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["columns"]) == 2
    assert data["columns"][0]["title"] == "Alpha"
    assert data["columns"][0]["cardIds"] == ["card-1"]
    assert data["cards"]["card-1"]["title"] == "Test Card"


@pytest.mark.anyio
async def test_put_board_persists(client):
    token = await login(client)
    headers = auth_header(token)

    board = {
        "columns": [
            {"id": "col-x", "title": "Only", "cardIds": ["card-x"]},
        ],
        "cards": {
            "card-x": {"id": "card-x", "title": "Persisted", "details": "Yes"},
        },
    }
    await client.put("/api/board", json=board, headers=headers)

    res = await client.get("/api/board", headers=headers)
    data = res.json()
    assert len(data["columns"]) == 1
    assert data["cards"]["card-x"]["title"] == "Persisted"


@pytest.mark.anyio
async def test_create_card(client):
    token = await login(client)
    headers = auth_header(token)

    # Get default board to have columns
    await client.get("/api/board", headers=headers)

    res = await client.post(
        "/api/board/cards",
        json={"column_id": "col-backlog", "title": "New Card", "details": "Details here"},
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "New Card"
    assert data["id"].startswith("card-")

    # Verify it's in the board
    board = await client.get("/api/board", headers=headers)
    board_data = board.json()
    assert data["id"] in board_data["cards"]
    assert data["id"] in board_data["columns"][0]["cardIds"]


@pytest.mark.anyio
async def test_create_card_invalid_column(client):
    token = await login(client)
    headers = auth_header(token)
    await client.get("/api/board", headers=headers)

    res = await client.post(
        "/api/board/cards",
        json={"column_id": "col-nonexistent", "title": "Orphan"},
        headers=headers,
    )
    assert res.status_code == 404


@pytest.mark.anyio
async def test_delete_card(client):
    token = await login(client)
    headers = auth_header(token)

    # Set up board with a card
    board = {
        "columns": [{"id": "col-a", "title": "A", "cardIds": ["card-del"]}],
        "cards": {"card-del": {"id": "card-del", "title": "To Delete", "details": "Bye"}},
    }
    await client.put("/api/board", json=board, headers=headers)

    res = await client.delete("/api/board/cards/card-del", headers=headers)
    assert res.status_code == 200

    # Verify card is gone
    board_res = await client.get("/api/board", headers=headers)
    assert "card-del" not in board_res.json()["cards"]


@pytest.mark.anyio
async def test_delete_card_not_found(client):
    token = await login(client)
    headers = auth_header(token)
    await client.get("/api/board", headers=headers)

    res = await client.delete("/api/board/cards/card-ghost", headers=headers)
    assert res.status_code == 404


@pytest.mark.anyio
async def test_patch_card(client):
    token = await login(client)
    headers = auth_header(token)

    board = {
        "columns": [{"id": "col-a", "title": "A", "cardIds": ["card-edit"]}],
        "cards": {"card-edit": {"id": "card-edit", "title": "Old Title", "details": "Old"}},
    }
    await client.put("/api/board", json=board, headers=headers)

    res = await client.patch(
        "/api/board/cards/card-edit",
        json={"title": "New Title", "details": "New Details"},
        headers=headers,
    )
    assert res.status_code == 200

    board_res = await client.get("/api/board", headers=headers)
    card = board_res.json()["cards"]["card-edit"]
    assert card["title"] == "New Title"
    assert card["details"] == "New Details"


@pytest.mark.anyio
async def test_patch_card_partial(client):
    token = await login(client)
    headers = auth_header(token)

    board = {
        "columns": [{"id": "col-a", "title": "A", "cardIds": ["card-p"]}],
        "cards": {"card-p": {"id": "card-p", "title": "Keep", "details": "Original"}},
    }
    await client.put("/api/board", json=board, headers=headers)

    await client.patch(
        "/api/board/cards/card-p", json={"title": "Changed"}, headers=headers
    )
    board_res = await client.get("/api/board", headers=headers)
    card = board_res.json()["cards"]["card-p"]
    assert card["title"] == "Changed"
    assert card["details"] == "Original"


@pytest.mark.anyio
async def test_rename_column(client):
    token = await login(client)
    headers = auth_header(token)
    await client.get("/api/board", headers=headers)

    res = await client.patch(
        "/api/board/columns/col-backlog",
        json={"title": "Icebox"},
        headers=headers,
    )
    assert res.status_code == 200

    board_res = await client.get("/api/board", headers=headers)
    col = board_res.json()["columns"][0]
    assert col["id"] == "col-backlog"
    assert col["title"] == "Icebox"


@pytest.mark.anyio
async def test_rename_column_not_found(client):
    token = await login(client)
    headers = auth_header(token)
    await client.get("/api/board", headers=headers)

    res = await client.patch(
        "/api/board/columns/col-ghost",
        json={"title": "Nope"},
        headers=headers,
    )
    assert res.status_code == 404


@pytest.mark.anyio
async def test_put_board_rolls_back_on_duplicate_column_id(client):
    """save_board must roll back if a mid-insert constraint violation occurs."""
    token = await login(client)
    headers = auth_header(token)

    # Establish an initial valid board
    initial = {
        "columns": [{"id": "col-keep", "title": "Keep", "cardIds": ["card-keep"]}],
        "cards": {"card-keep": {"id": "card-keep", "title": "Original", "details": "Data"}},
    }
    res = await client.put("/api/board", json=initial, headers=headers)
    assert res.status_code == 200

    # Attempt to save a board with duplicate column IDs — will fail mid-insert
    bad_board = {
        "columns": [
            {"id": "col-dup", "title": "First", "cardIds": []},
            {"id": "col-dup", "title": "Duplicate", "cardIds": []},
        ],
        "cards": {},
    }
    res = await client.put("/api/board", json=bad_board, headers=headers)
    # Must fail — duplicate primary key
    assert res.status_code in (400, 422, 500)

    # Original board must still be intact (rollback succeeded)
    board_res = await client.get("/api/board", headers=headers)
    data = board_res.json()
    assert data["columns"][0]["title"] == "Keep"
    assert "card-keep" in data["cards"]


@pytest.mark.anyio
async def test_put_board_reorders_columns(client):
    token = await login(client)
    headers = auth_header(token)

    board = {
        "columns": [
            {"id": "col-b", "title": "Beta", "cardIds": ["card-2"]},
            {"id": "col-a", "title": "Alpha", "cardIds": ["card-1"]},
        ],
        "cards": {
            "card-1": {"id": "card-1", "title": "One", "details": "First"},
            "card-2": {"id": "card-2", "title": "Two", "details": "Second"},
        },
    }
    res = await client.put("/api/board", json=board, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["columns"][0]["id"] == "col-b"
    assert data["columns"][1]["id"] == "col-a"
    assert data["columns"][0]["cardIds"] == ["card-2"]
