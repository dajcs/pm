import pytest
from conftest import auth_header, login


@pytest.mark.anyio
async def test_list_boards_default(client):
    token = await login(client)
    headers = auth_header(token)
    # Trigger lazy board creation
    await client.get("/api/board", headers=headers)
    res = await client.get("/api/boards", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["name"] == "My Board"


@pytest.mark.anyio
async def test_create_board(client):
    token = await login(client)
    headers = auth_header(token)
    # Trigger lazy board creation for "My Board"
    await client.get("/api/board", headers=headers)

    res = await client.post("/api/boards", json={"name": "Sprint 1"}, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Sprint 1"
    assert "id" in data

    # Verify it's in the list
    list_res = await client.get("/api/boards", headers=headers)
    names = [b["name"] for b in list_res.json()]
    assert "Sprint 1" in names
    assert "My Board" in names


@pytest.mark.anyio
async def test_new_board_has_default_columns(client):
    token = await login(client)
    headers = auth_header(token)
    res = await client.post("/api/boards", json={"name": "New Board"}, headers=headers)
    board_id = res.json()["id"]

    board_res = await client.get(f"/api/board?board_id={board_id}", headers=headers)
    assert board_res.status_code == 200
    data = board_res.json()
    assert len(data["columns"]) == 5


@pytest.mark.anyio
async def test_board_id_selects_correct_board(client):
    token = await login(client)
    headers = auth_header(token)

    # Create second board
    res = await client.post("/api/boards", json={"name": "Second"}, headers=headers)
    second_id = res.json()["id"]

    # Ensure first board exists
    await client.get("/api/board", headers=headers)
    boards = await client.get("/api/boards", headers=headers)
    first_id = boards.json()[0]["id"]

    board1 = await client.get(f"/api/board?board_id={first_id}", headers=headers)
    board2 = await client.get(f"/api/board?board_id={second_id}", headers=headers)
    assert board1.status_code == 200
    assert board2.status_code == 200
    assert len(board1.json()["columns"]) == 5
    assert len(board2.json()["columns"]) == 5


@pytest.mark.anyio
async def test_rename_board(client):
    token = await login(client)
    headers = auth_header(token)
    await client.get("/api/board", headers=headers)
    boards = await client.get("/api/boards", headers=headers)
    board_id = boards.json()[0]["id"]

    res = await client.patch(f"/api/boards/{board_id}", json={"name": "Renamed"}, headers=headers)
    assert res.status_code == 200

    boards_res = await client.get("/api/boards", headers=headers)
    assert boards_res.json()[0]["name"] == "Renamed"


@pytest.mark.anyio
async def test_delete_board(client):
    token = await login(client)
    headers = auth_header(token)
    # Ensure default board exists first
    await client.get("/api/board", headers=headers)

    # Create a second board
    res = await client.post("/api/boards", json={"name": "Temp"}, headers=headers)
    new_id = res.json()["id"]

    del_res = await client.delete(f"/api/boards/{new_id}", headers=headers)
    assert del_res.status_code == 200

    boards_res = await client.get("/api/boards", headers=headers)
    ids = [b["id"] for b in boards_res.json()]
    assert new_id not in ids


@pytest.mark.anyio
async def test_cannot_delete_last_board(client):
    token = await login(client)
    headers = auth_header(token)
    await client.get("/api/board", headers=headers)
    boards = await client.get("/api/boards", headers=headers)
    board_id = boards.json()[0]["id"]

    res = await client.delete(f"/api/boards/{board_id}", headers=headers)
    assert res.status_code == 400


@pytest.mark.anyio
async def test_cannot_access_other_users_board(client):
    """User cannot access another user's board via board_id."""
    # Register a second user
    res = await client.post(
        "/api/auth/register", json={"username": "other", "password": "password123"}
    )
    other_token = res.json()["token"]
    other_headers = auth_header(other_token)

    # Ensure the other user has a board
    await client.get("/api/board", headers=other_headers)
    boards = await client.get("/api/boards", headers=other_headers)
    other_board_id = boards.json()[0]["id"]

    # Try to access with original user's token
    token = await login(client)
    headers = auth_header(token)
    res = await client.get(f"/api/board?board_id={other_board_id}", headers=headers)
    assert res.status_code == 404


@pytest.mark.anyio
async def test_add_column(client):
    token = await login(client)
    headers = auth_header(token)
    await client.get("/api/board", headers=headers)  # ensure board exists

    res = await client.post(
        "/api/board/columns", json={"title": "Review"}, headers=headers
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Review"
    assert data["id"].startswith("col-")

    # Verify it's in the board
    board_res = await client.get("/api/board", headers=headers)
    titles = [c["title"] for c in board_res.json()["columns"]]
    assert "Review" in titles


@pytest.mark.anyio
async def test_delete_column(client):
    token = await login(client)
    headers = auth_header(token)
    await client.get("/api/board", headers=headers)

    # Add a column to delete
    add_res = await client.post(
        "/api/board/columns", json={"title": "Temp Col"}, headers=headers
    )
    col_id = add_res.json()["id"]

    del_res = await client.delete(f"/api/board/columns/{col_id}", headers=headers)
    assert del_res.status_code == 200

    board_res = await client.get("/api/board", headers=headers)
    ids = [c["id"] for c in board_res.json()["columns"]]
    assert col_id not in ids


@pytest.mark.anyio
async def test_delete_column_not_found(client):
    token = await login(client)
    headers = auth_header(token)
    await client.get("/api/board", headers=headers)

    res = await client.delete("/api/board/columns/col-ghost", headers=headers)
    assert res.status_code == 404
