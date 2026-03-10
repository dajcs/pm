"""Tests for card dependencies and cross-board dashboard."""
import pytest
from conftest import auth_header, login


async def _setup_two_cards(client, headers):
    await client.get("/api/board", headers=headers)
    boards = (await client.get("/api/boards", headers=headers)).json()
    board_id = boards[0]["id"]
    board = (await client.get(f"/api/board?board_id={board_id}", headers=headers)).json()
    col_id = board["columns"][0]["id"]

    async def mk(title):
        r = await client.post(
            f"/api/board/cards?board_id={board_id}",
            json={"column_id": col_id, "title": title, "details": "d"},
            headers=headers,
        )
        return r.json()["id"]

    card_a = await mk("Card A")
    card_b = await mk("Card B")
    return board_id, card_a, card_b


@pytest.mark.anyio
async def test_add_dependency(client):
    token = await login(client)
    h = auth_header(token)
    board_id, card_a, card_b = await _setup_two_cards(client, h)

    r = await client.post(
        f"/api/board/cards/{card_a}/dependencies?board_id={board_id}",
        json={"depends_on_id": card_b},
        headers=h,
    )
    assert r.status_code == 200


@pytest.mark.anyio
async def test_get_dependencies(client):
    token = await login(client)
    h = auth_header(token)
    board_id, card_a, card_b = await _setup_two_cards(client, h)

    await client.post(
        f"/api/board/cards/{card_a}/dependencies?board_id={board_id}",
        json={"depends_on_id": card_b},
        headers=h,
    )

    r = await client.get(
        f"/api/board/cards/{card_a}/dependencies?board_id={board_id}", headers=h
    )
    assert r.status_code == 200
    data = r.json()
    assert any(d["id"] == card_b for d in data["blocked_by"])
    assert data["blocking"] == []


@pytest.mark.anyio
async def test_dependency_is_bidirectional_view(client):
    """card_b should show card_a as 'blocking' it."""
    token = await login(client)
    h = auth_header(token)
    board_id, card_a, card_b = await _setup_two_cards(client, h)

    await client.post(
        f"/api/board/cards/{card_a}/dependencies?board_id={board_id}",
        json={"depends_on_id": card_b},
        headers=h,
    )

    r = await client.get(
        f"/api/board/cards/{card_b}/dependencies?board_id={board_id}", headers=h
    )
    data = r.json()
    assert any(d["id"] == card_a for d in data["blocking"])
    assert data["blocked_by"] == []


@pytest.mark.anyio
async def test_self_dependency_rejected(client):
    token = await login(client)
    h = auth_header(token)
    board_id, card_a, _ = await _setup_two_cards(client, h)

    r = await client.post(
        f"/api/board/cards/{card_a}/dependencies?board_id={board_id}",
        json={"depends_on_id": card_a},
        headers=h,
    )
    assert r.status_code == 400


@pytest.mark.anyio
async def test_duplicate_dependency_rejected(client):
    token = await login(client)
    h = auth_header(token)
    board_id, card_a, card_b = await _setup_two_cards(client, h)

    await client.post(
        f"/api/board/cards/{card_a}/dependencies?board_id={board_id}",
        json={"depends_on_id": card_b},
        headers=h,
    )
    r = await client.post(
        f"/api/board/cards/{card_a}/dependencies?board_id={board_id}",
        json={"depends_on_id": card_b},
        headers=h,
    )
    assert r.status_code == 409


@pytest.mark.anyio
async def test_remove_dependency(client):
    token = await login(client)
    h = auth_header(token)
    board_id, card_a, card_b = await _setup_two_cards(client, h)

    await client.post(
        f"/api/board/cards/{card_a}/dependencies?board_id={board_id}",
        json={"depends_on_id": card_b},
        headers=h,
    )
    r = await client.delete(
        f"/api/board/cards/{card_a}/dependencies/{card_b}?board_id={board_id}", headers=h
    )
    assert r.status_code == 200

    deps = (await client.get(
        f"/api/board/cards/{card_a}/dependencies?board_id={board_id}", headers=h
    )).json()
    assert deps["blocked_by"] == []


@pytest.mark.anyio
async def test_remove_nonexistent_dependency(client):
    token = await login(client)
    h = auth_header(token)
    board_id, card_a, card_b = await _setup_two_cards(client, h)

    r = await client.delete(
        f"/api/board/cards/{card_a}/dependencies/{card_b}?board_id={board_id}", headers=h
    )
    assert r.status_code == 404


@pytest.mark.anyio
async def test_dependency_cascade_delete(client):
    """Deleting a card removes dependencies referencing it."""
    token = await login(client)
    h = auth_header(token)
    board_id, card_a, card_b = await _setup_two_cards(client, h)

    await client.post(
        f"/api/board/cards/{card_a}/dependencies?board_id={board_id}",
        json={"depends_on_id": card_b},
        headers=h,
    )
    # Delete card_b (the dependency target)
    await client.delete(f"/api/board/cards/{card_b}?board_id={board_id}", headers=h)

    # card_a's blocked_by should be empty
    deps = (await client.get(
        f"/api/board/cards/{card_a}/dependencies?board_id={board_id}", headers=h
    )).json()
    assert deps["blocked_by"] == []


# ── Dashboard ─────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_dashboard_empty(client):
    token = await login(client)
    h = auth_header(token)
    await client.get("/api/board", headers=h)  # trigger creation

    r = await client.get("/api/dashboard", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "overdue" in data
    assert "due_soon" in data
    assert data["total_overdue"] == 0
    assert data["total_due_soon"] == 0


@pytest.mark.anyio
async def test_dashboard_shows_overdue_card(client):
    token = await login(client)
    h = auth_header(token)
    board_id, card_a, _ = await _setup_two_cards(client, h)

    # Set a past due date
    await client.patch(
        f"/api/board/cards/{card_a}?board_id={board_id}",
        json={"due_date": "2020-01-01"},
        headers=h,
    )

    r = await client.get("/api/dashboard", headers=h)
    data = r.json()
    assert data["total_overdue"] >= 1
    assert any(c["id"] == card_a for c in data["overdue"])


@pytest.mark.anyio
async def test_dashboard_shows_due_soon_card(client):
    token = await login(client)
    h = auth_header(token)
    board_id, _, card_b = await _setup_two_cards(client, h)

    # Set due date to tomorrow
    from datetime import date, timedelta
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    await client.patch(
        f"/api/board/cards/{card_b}?board_id={board_id}",
        json={"due_date": tomorrow},
        headers=h,
    )

    r = await client.get("/api/dashboard", headers=h)
    data = r.json()
    assert data["total_due_soon"] >= 1


@pytest.mark.anyio
async def test_dashboard_excludes_archived(client):
    token = await login(client)
    h = auth_header(token)
    board_id, card_a, _ = await _setup_two_cards(client, h)

    await client.patch(
        f"/api/board/cards/{card_a}?board_id={board_id}",
        json={"due_date": "2020-01-01"},
        headers=h,
    )
    await client.post(f"/api/board/cards/{card_a}/archive?board_id={board_id}", headers=h)

    r = await client.get("/api/dashboard", headers=h)
    data = r.json()
    assert not any(c["id"] == card_a for c in data["overdue"])
