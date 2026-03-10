"""Tests for board sharing/collaboration and board templates."""
import pytest
from conftest import auth_header, login


async def _register(client, username, password="password123"):
    r = await client.post("/api/auth/register", json={"username": username, "password": password})
    assert r.status_code in (200, 201)
    token = r.json()["token"]
    return auth_header(token)


async def _get_board_id(client, headers):
    await client.get("/api/board", headers=headers)
    boards = (await client.get("/api/boards", headers=headers)).json()
    return boards[0]["id"]


# ── Board Sharing ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_invite_member(client):
    h_owner = await _register(client, "shareown1")
    h_member = await _register(client, "sharemem1")
    board_id = await _get_board_id(client, h_owner)

    r = await client.post(
        f"/api/boards/{board_id}/invite",
        json={"username": "sharemem1"},
        headers=h_owner,
    )
    assert r.status_code == 200


@pytest.mark.anyio
async def test_member_can_access_board(client):
    h_owner = await _register(client, "shareown2")
    h_member = await _register(client, "sharemem2")
    board_id = await _get_board_id(client, h_owner)

    await client.post(f"/api/boards/{board_id}/invite", json={"username": "sharemem2"}, headers=h_owner)

    r = await client.get(f"/api/board?board_id={board_id}", headers=h_member)
    assert r.status_code == 200


@pytest.mark.anyio
async def test_non_member_cannot_access_board(client):
    h_owner = await _register(client, "shareown3")
    h_other = await _register(client, "shareotr3")
    board_id = await _get_board_id(client, h_owner)

    r = await client.get(f"/api/board?board_id={board_id}", headers=h_other)
    assert r.status_code == 404


@pytest.mark.anyio
async def test_member_can_create_card(client):
    h_owner = await _register(client, "shareown4")
    h_member = await _register(client, "sharemem4")
    board_id = await _get_board_id(client, h_owner)
    board = (await client.get(f"/api/board?board_id={board_id}", headers=h_owner)).json()
    col_id = board["columns"][0]["id"]

    await client.post(f"/api/boards/{board_id}/invite", json={"username": "sharemem4"}, headers=h_owner)

    r = await client.post(
        f"/api/board/cards?board_id={board_id}",
        json={"column_id": col_id, "title": "Member card", "details": "d"},
        headers=h_member,
    )
    assert r.status_code in (200, 201)


@pytest.mark.anyio
async def test_shared_board_appears_in_member_list(client):
    h_owner = await _register(client, "shareown5")
    h_member = await _register(client, "sharemem5")
    board_id = await _get_board_id(client, h_owner)

    await client.post(f"/api/boards/{board_id}/invite", json={"username": "sharemem5"}, headers=h_owner)

    boards = (await client.get("/api/boards", headers=h_member)).json()
    assert any(b["id"] == board_id for b in boards)


@pytest.mark.anyio
async def test_members_with_roles_endpoint(client):
    h_owner = await _register(client, "shareown6")
    h_member = await _register(client, "sharemem6")
    board_id = await _get_board_id(client, h_owner)

    await client.post(f"/api/boards/{board_id}/invite", json={"username": "sharemem6"}, headers=h_owner)

    r = await client.get(f"/api/boards/{board_id}/members/roles", headers=h_owner)
    assert r.status_code == 200
    members = r.json()
    roles = {m["username"]: m["role"] for m in members}
    assert roles["shareown6"] == "owner"
    assert roles["sharemem6"] == "member"


@pytest.mark.anyio
async def test_remove_member(client):
    h_owner = await _register(client, "shareown7")
    h_member = await _register(client, "sharemem7")
    board_id = await _get_board_id(client, h_owner)

    await client.post(f"/api/boards/{board_id}/invite", json={"username": "sharemem7"}, headers=h_owner)
    r = await client.delete(f"/api/boards/{board_id}/members/sharemem7", headers=h_owner)
    assert r.status_code == 200

    # Member should no longer access board
    r = await client.get(f"/api/board?board_id={board_id}", headers=h_member)
    assert r.status_code == 404


@pytest.mark.anyio
async def test_member_cannot_invite_others(client):
    h_owner = await _register(client, "shareown8")
    h_member = await _register(client, "sharemem8")
    h_other = await _register(client, "shareotr8")
    board_id = await _get_board_id(client, h_owner)

    await client.post(f"/api/boards/{board_id}/invite", json={"username": "sharemem8"}, headers=h_owner)

    r = await client.post(
        f"/api/boards/{board_id}/invite",
        json={"username": "shareotr8"},
        headers=h_member,
    )
    assert r.status_code == 403


@pytest.mark.anyio
async def test_invite_nonexistent_user(client):
    h_owner = await _register(client, "shareown9")
    board_id = await _get_board_id(client, h_owner)

    r = await client.post(
        f"/api/boards/{board_id}/invite",
        json={"username": "nobody_xyz_9999"},
        headers=h_owner,
    )
    assert r.status_code == 404


@pytest.mark.anyio
async def test_invite_duplicate_rejected(client):
    h_owner = await _register(client, "shareown10")
    h_member = await _register(client, "sharemem10")
    board_id = await _get_board_id(client, h_owner)

    await client.post(f"/api/boards/{board_id}/invite", json={"username": "sharemem10"}, headers=h_owner)
    r = await client.post(f"/api/boards/{board_id}/invite", json={"username": "sharemem10"}, headers=h_owner)
    assert r.status_code == 409


@pytest.mark.anyio
async def test_member_cannot_delete_board(client):
    """Members should not be able to delete boards they don't own."""
    h_owner = await _register(client, "shareown11")
    h_member = await _register(client, "sharemem11")
    board_id = await _get_board_id(client, h_owner)

    await client.post(f"/api/boards/{board_id}/invite", json={"username": "sharemem11"}, headers=h_owner)

    # Member tries to delete - delete_board checks ownership only
    r = await client.delete(f"/api/boards/{board_id}", headers=h_member)
    assert r.status_code in (403, 404)


# ── Board Templates ────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_list_templates(client):
    token = await login(client)
    h = auth_header(token)
    r = await client.get("/api/boards/templates", headers=h)
    assert r.status_code == 200
    templates = r.json()
    names = [t["name"] for t in templates]
    assert "sprint" in names
    assert "personal" in names


@pytest.mark.anyio
async def test_create_board_from_template(client):
    token = await login(client)
    h = auth_header(token)
    r = await client.post(
        "/api/boards/from-template",
        json={"name": "Sprint Board", "template": "sprint"},
        headers=h,
    )
    assert r.status_code == 201
    assert r.json()["template"] == "sprint"


@pytest.mark.anyio
async def test_template_board_has_correct_columns(client):
    token = await login(client)
    h = auth_header(token)
    r = await client.post(
        "/api/boards/from-template",
        json={"name": "Marketing", "template": "marketing"},
        headers=h,
    )
    board_id = r.json()["id"]
    board = (await client.get(f"/api/board?board_id={board_id}", headers=h)).json()
    col_titles = [c["title"] for c in board["columns"]]
    for expected in ["Ideas", "Planning", "In Progress", "Review", "Published"]:
        assert expected in col_titles


@pytest.mark.anyio
async def test_unknown_template_rejected(client):
    token = await login(client)
    h = auth_header(token)
    r = await client.post(
        "/api/boards/from-template",
        json={"name": "Bad", "template": "nonexistent_template"},
        headers=h,
    )
    assert r.status_code == 400


@pytest.mark.anyio
async def test_invite_activity_logged(client):
    h_owner = await _register(client, "shareown12")
    h_member = await _register(client, "sharemem12")
    board_id = await _get_board_id(client, h_owner)

    await client.post(f"/api/boards/{board_id}/invite", json={"username": "sharemem12"}, headers=h_owner)

    activity = (await client.get(f"/api/boards/{board_id}/activity", headers=h_owner)).json()
    assert any("invited" in e["action"] for e in activity)
