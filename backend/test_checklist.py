import pytest
from conftest import auth_header, login


async def _setup_card(client, headers, card_id="card-chk"):
    board = {
        "columns": [{"id": "col-a", "title": "A", "cardIds": [card_id]}],
        "cards": {card_id: {"id": card_id, "title": "Task", "details": "d"}},
    }
    await client.put("/api/board", json=board, headers=headers)
    return card_id


@pytest.mark.anyio
async def test_checklist_empty_by_default(client):
    token = await login(client)
    headers = auth_header(token)
    card_id = await _setup_card(client, headers)

    res = await client.get(f"/api/board/cards/{card_id}/checklist", headers=headers)
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.anyio
async def test_add_checklist_item(client):
    token = await login(client)
    headers = auth_header(token)
    card_id = await _setup_card(client, headers)

    res = await client.post(
        f"/api/board/cards/{card_id}/checklist",
        json={"text": "Write tests"},
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["text"] == "Write tests"
    assert data["checked"] is False
    assert "id" in data


@pytest.mark.anyio
async def test_checklist_appears_in_get(client):
    token = await login(client)
    headers = auth_header(token)
    card_id = await _setup_card(client, headers)

    await client.post(
        f"/api/board/cards/{card_id}/checklist",
        json={"text": "Step one"},
        headers=headers,
    )
    await client.post(
        f"/api/board/cards/{card_id}/checklist",
        json={"text": "Step two"},
        headers=headers,
    )

    res = await client.get(f"/api/board/cards/{card_id}/checklist", headers=headers)
    assert res.status_code == 200
    texts = [item["text"] for item in res.json()]
    assert "Step one" in texts
    assert "Step two" in texts


@pytest.mark.anyio
async def test_check_item(client):
    token = await login(client)
    headers = auth_header(token)
    card_id = await _setup_card(client, headers)

    add_res = await client.post(
        f"/api/board/cards/{card_id}/checklist",
        json={"text": "Do thing"},
        headers=headers,
    )
    item_id = add_res.json()["id"]

    res = await client.patch(
        f"/api/board/cards/{card_id}/checklist/{item_id}",
        json={"checked": True},
        headers=headers,
    )
    assert res.status_code == 200

    items = await client.get(f"/api/board/cards/{card_id}/checklist", headers=headers)
    item = next(i for i in items.json() if i["id"] == item_id)
    assert item["checked"] is True


@pytest.mark.anyio
async def test_uncheck_item(client):
    token = await login(client)
    headers = auth_header(token)
    card_id = await _setup_card(client, headers)

    add_res = await client.post(
        f"/api/board/cards/{card_id}/checklist",
        json={"text": "Done thing"},
        headers=headers,
    )
    item_id = add_res.json()["id"]
    await client.patch(
        f"/api/board/cards/{card_id}/checklist/{item_id}",
        json={"checked": True},
        headers=headers,
    )
    res = await client.patch(
        f"/api/board/cards/{card_id}/checklist/{item_id}",
        json={"checked": False},
        headers=headers,
    )
    assert res.status_code == 200
    items = await client.get(f"/api/board/cards/{card_id}/checklist", headers=headers)
    item = next(i for i in items.json() if i["id"] == item_id)
    assert item["checked"] is False


@pytest.mark.anyio
async def test_edit_checklist_text(client):
    token = await login(client)
    headers = auth_header(token)
    card_id = await _setup_card(client, headers)

    add_res = await client.post(
        f"/api/board/cards/{card_id}/checklist",
        json={"text": "Old text"},
        headers=headers,
    )
    item_id = add_res.json()["id"]

    await client.patch(
        f"/api/board/cards/{card_id}/checklist/{item_id}",
        json={"text": "New text"},
        headers=headers,
    )
    items = await client.get(f"/api/board/cards/{card_id}/checklist", headers=headers)
    item = next(i for i in items.json() if i["id"] == item_id)
    assert item["text"] == "New text"


@pytest.mark.anyio
async def test_delete_checklist_item(client):
    token = await login(client)
    headers = auth_header(token)
    card_id = await _setup_card(client, headers)

    add_res = await client.post(
        f"/api/board/cards/{card_id}/checklist",
        json={"text": "To delete"},
        headers=headers,
    )
    item_id = add_res.json()["id"]

    res = await client.delete(
        f"/api/board/cards/{card_id}/checklist/{item_id}",
        headers=headers,
    )
    assert res.status_code == 200

    items = await client.get(f"/api/board/cards/{card_id}/checklist", headers=headers)
    assert not any(i["id"] == item_id for i in items.json())


@pytest.mark.anyio
async def test_checklist_summary_in_board(client):
    """Board load returns checklist_total and checklist_done per card."""
    token = await login(client)
    headers = auth_header(token)
    card_id = await _setup_card(client, headers)

    add1 = await client.post(
        f"/api/board/cards/{card_id}/checklist",
        json={"text": "Item 1"},
        headers=headers,
    )
    add2 = await client.post(
        f"/api/board/cards/{card_id}/checklist",
        json={"text": "Item 2"},
        headers=headers,
    )
    item1_id = add1.json()["id"]
    await client.patch(
        f"/api/board/cards/{card_id}/checklist/{item1_id}",
        json={"checked": True},
        headers=headers,
    )

    board_res = await client.get("/api/board", headers=headers)
    card = board_res.json()["cards"][card_id]
    assert card["checklist_total"] == 2
    assert card["checklist_done"] == 1


@pytest.mark.anyio
async def test_checklist_deleted_with_card(client):
    """Deleting a card cascades to its checklist items."""
    token = await login(client)
    headers = auth_header(token)
    card_id = await _setup_card(client, headers, card_id="card-cascade")

    await client.post(
        f"/api/board/cards/{card_id}/checklist",
        json={"text": "Should be gone"},
        headers=headers,
    )
    await client.delete(f"/api/board/cards/{card_id}", headers=headers)

    # Card is gone; checklist endpoint returns 404
    res = await client.get(f"/api/board/cards/{card_id}/checklist", headers=headers)
    assert res.status_code == 404


@pytest.mark.anyio
async def test_checklist_requires_auth(client):
    res = await client.get("/api/board/cards/card-x/checklist")
    assert res.status_code == 401


@pytest.mark.anyio
async def test_checklist_wrong_board(client):
    """Cannot access checklist of another user's card."""
    res = await client.post(
        "/api/auth/register",
        json={"username": "chkother", "password": "password123"},
    )
    other_token = res.json()["token"]
    other_headers = auth_header(other_token)

    await _setup_card(
        client, other_headers, card_id="card-other-chk"
    )

    token = await login(client)
    headers = auth_header(token)
    res = await client.get(
        "/api/board/cards/card-other-chk/checklist",
        headers=headers,
    )
    assert res.status_code == 404
