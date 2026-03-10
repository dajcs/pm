"""Tests for card assignment and enhanced search."""
import pytest
from conftest import auth_header, login


async def _board_with_card(client, headers, title="Assignable", details="some details"):
    board_data = (await client.get("/api/board", headers=headers)).json()
    col_id = board_data["columns"][0]["id"]
    resp = await client.post(
        "/api/board/cards",
        json={"column_id": col_id, "title": title, "details": details},
        headers=headers,
    )
    return resp.json()["id"]


# ── Assignment ────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_card_has_no_assignment_by_default(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _board_with_card(client, h)
    board = (await client.get("/api/board", headers=h)).json()
    assert board["cards"][card_id]["assigned_to"] is None


@pytest.mark.anyio
async def test_assign_card_to_user(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _board_with_card(client, h)
    resp = await client.patch(
        f"/api/board/cards/{card_id}",
        json={"assigned_to": "user"},
        headers=h,
    )
    assert resp.status_code == 200
    board = (await client.get("/api/board", headers=h)).json()
    assert board["cards"][card_id]["assigned_to"] == "user"


@pytest.mark.anyio
async def test_unassign_card(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _board_with_card(client, h)
    await client.patch(f"/api/board/cards/{card_id}", json={"assigned_to": "user"}, headers=h)
    resp = await client.patch(f"/api/board/cards/{card_id}", json={"assigned_to": None}, headers=h)
    assert resp.status_code == 200
    board = (await client.get("/api/board", headers=h)).json()
    assert board["cards"][card_id]["assigned_to"] is None


@pytest.mark.anyio
async def test_assignment_persists_through_save_board(client):
    token = await login(client)
    h = auth_header(token)
    board = {
        "columns": [{"id": "col-a", "title": "A", "cardIds": ["card-asgn"]}],
        "cards": {"card-asgn": {"id": "card-asgn", "title": "Assigned", "details": "d",
                                "assigned_to": "user"}},
    }
    await client.put("/api/board", json=board, headers=h)
    result = (await client.get("/api/board", headers=h)).json()
    assert result["cards"]["card-asgn"]["assigned_to"] == "user"


# ── Search ────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_search_by_title(client):
    token = await login(client)
    h = auth_header(token)
    await _board_with_card(client, h, title="Unique title XYZ", details="irrelevant")
    await _board_with_card(client, h, title="Other card", details="nothing")
    resp = await client.get("/api/board/search?q=XYZ", headers=h)
    assert resp.status_code == 200
    ids = resp.json()
    assert len(ids) == 1


@pytest.mark.anyio
async def test_search_by_details(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _board_with_card(client, h, title="Plain title", details="detailed description MARKER")
    await _board_with_card(client, h, title="Other", details="nothing special")
    resp = await client.get("/api/board/search?q=MARKER", headers=h)
    assert resp.status_code == 200
    assert card_id in resp.json()


@pytest.mark.anyio
async def test_search_by_comment(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _board_with_card(client, h, title="Card to comment", details="d")
    await client.post(
        f"/api/board/cards/{card_id}/comments",
        json={"text": "Important note SEARCHTOKEN"},
        headers=h,
    )
    resp = await client.get("/api/board/search?q=SEARCHTOKEN", headers=h)
    assert resp.status_code == 200
    assert card_id in resp.json()


@pytest.mark.anyio
async def test_search_case_insensitive(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _board_with_card(client, h, title="CamelCaseTitle", details="d")
    resp = await client.get("/api/board/search?q=camelcase", headers=h)
    assert resp.status_code == 200
    assert card_id in resp.json()


@pytest.mark.anyio
async def test_search_empty_result(client):
    token = await login(client)
    h = auth_header(token)
    await client.get("/api/board", headers=h)
    resp = await client.get("/api/board/search?q=NORESULTEXPECTED999", headers=h)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_search_excludes_archived(client):
    token = await login(client)
    h = auth_header(token)
    card_id = await _board_with_card(client, h, title="ArchivedSearch UNIQUE", details="d")
    await client.post(f"/api/board/cards/{card_id}/archive", headers=h)
    resp = await client.get("/api/board/search?q=ArchivedSearch", headers=h)
    assert resp.status_code == 200
    assert card_id not in resp.json()


@pytest.mark.anyio
async def test_search_requires_auth(client):
    resp = await client.get("/api/board/search?q=test")
    assert resp.status_code == 401


# ── Board members ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_board_members_includes_owner(client):
    token = await login(client)
    h = auth_header(token)
    await client.get("/api/board", headers=h)
    boards = (await client.get("/api/boards", headers=h)).json()
    bid = boards[0]["id"]
    resp = await client.get(f"/api/boards/{bid}/members", headers=h)
    assert resp.status_code == 200
    assert "user" in resp.json()


@pytest.mark.anyio
async def test_board_members_requires_auth(client):
    token = await login(client)
    h = auth_header(token)
    await client.get("/api/board", headers=h)
    boards = (await client.get("/api/boards", headers=h)).json()
    bid = boards[0]["id"]
    resp = await client.get(f"/api/boards/{bid}/members")
    assert resp.status_code == 401
