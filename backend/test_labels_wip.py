import pytest
from conftest import auth_header, login


# ── Labels ───────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_card_has_empty_labels_by_default(client):
    token = await login(client)
    headers = auth_header(token)
    board_data = (await client.get("/api/board", headers=headers)).json()
    col_id = board_data["columns"][0]["id"]

    res = await client.post(
        "/api/board/cards",
        json={"column_id": col_id, "title": "No labels"},
        headers=headers,
    )
    assert res.status_code == 201
    card_id = res.json()["id"]

    board = await client.get("/api/board", headers=headers)
    assert board.json()["cards"][card_id]["labels"] == []


@pytest.mark.anyio
async def test_update_card_labels(client):
    token = await login(client)
    headers = auth_header(token)

    board = {
        "columns": [{"id": "col-a", "title": "A", "cardIds": ["card-lbl"]}],
        "cards": {"card-lbl": {"id": "card-lbl", "title": "Label me", "details": "d"}},
    }
    await client.put("/api/board", json=board, headers=headers)

    res = await client.patch(
        "/api/board/cards/card-lbl",
        json={"labels": ["bug", "urgent"]},
        headers=headers,
    )
    assert res.status_code == 200

    board_res = await client.get("/api/board", headers=headers)
    labels = board_res.json()["cards"]["card-lbl"]["labels"]
    assert "bug" in labels
    assert "urgent" in labels


@pytest.mark.anyio
async def test_clear_card_labels(client):
    token = await login(client)
    headers = auth_header(token)

    board = {
        "columns": [{"id": "col-a", "title": "A", "cardIds": ["card-clrlbl"]}],
        "cards": {"card-clrlbl": {"id": "card-clrlbl", "title": "Labels", "details": "d",
                                   "labels": ["bug", "feature"]}},
    }
    await client.put("/api/board", json=board, headers=headers)

    res = await client.patch(
        "/api/board/cards/card-clrlbl",
        json={"labels": []},
        headers=headers,
    )
    assert res.status_code == 200

    board_res = await client.get("/api/board", headers=headers)
    assert board_res.json()["cards"]["card-clrlbl"]["labels"] == []


@pytest.mark.anyio
async def test_labels_persist_through_save_board(client):
    token = await login(client)
    headers = auth_header(token)

    board = {
        "columns": [{"id": "col-a", "title": "A", "cardIds": ["card-sv"]}],
        "cards": {
            "card-sv": {
                "id": "card-sv", "title": "Saved", "details": "d",
                "labels": ["feature", "docs"],
            }
        },
    }
    res = await client.put("/api/board", json=board, headers=headers)
    assert res.status_code == 200

    board_res = await client.get("/api/board", headers=headers)
    assert set(board_res.json()["cards"]["card-sv"]["labels"]) == {"feature", "docs"}


# ── WIP limits ────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_column_has_no_wip_limit_by_default(client):
    token = await login(client)
    headers = auth_header(token)

    board_res = await client.get("/api/board", headers=headers)
    for col in board_res.json()["columns"]:
        assert col["wip_limit"] is None


@pytest.mark.anyio
async def test_set_column_wip_limit(client):
    token = await login(client)
    headers = auth_header(token)
    board_data = (await client.get("/api/board", headers=headers)).json()
    col_id = board_data["columns"][0]["id"]

    res = await client.put(
        f"/api/board/columns/{col_id}/wip-limit",
        json={"wip_limit": 3},
        headers=headers,
    )
    assert res.status_code == 200

    board_res = await client.get("/api/board", headers=headers)
    backlog = next(c for c in board_res.json()["columns"] if c["id"] == col_id)
    assert backlog["wip_limit"] == 3


@pytest.mark.anyio
async def test_clear_column_wip_limit(client):
    token = await login(client)
    headers = auth_header(token)
    board_data = (await client.get("/api/board", headers=headers)).json()
    col_id = board_data["columns"][0]["id"]

    await client.put(f"/api/board/columns/{col_id}/wip-limit", json={"wip_limit": 5}, headers=headers)
    res = await client.put(f"/api/board/columns/{col_id}/wip-limit", json={"wip_limit": None}, headers=headers)
    assert res.status_code == 200

    board_res = await client.get("/api/board", headers=headers)
    backlog = next(c for c in board_res.json()["columns"] if c["id"] == col_id)
    assert backlog["wip_limit"] is None


@pytest.mark.anyio
async def test_wip_limit_wrong_column(client):
    token = await login(client)
    headers = auth_header(token)
    await client.get("/api/board", headers=headers)

    res = await client.put(
        "/api/board/columns/col-ghost/wip-limit",
        json={"wip_limit": 3},
        headers=headers,
    )
    assert res.status_code == 404


@pytest.mark.anyio
async def test_wip_limit_persists_through_save_board(client):
    token = await login(client)
    headers = auth_header(token)

    board = {
        "columns": [{"id": "col-wip", "title": "WIP", "cardIds": [], "wip_limit": 4}],
        "cards": {},
    }
    res = await client.put("/api/board", json=board, headers=headers)
    assert res.status_code == 200

    board_res = await client.get("/api/board", headers=headers)
    col = board_res.json()["columns"][0]
    assert col["wip_limit"] == 4
