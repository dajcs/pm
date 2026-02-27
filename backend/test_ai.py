"""Tests for the AI connectivity module."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from conftest import auth_header, login
from main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _mock_completion(content: str) -> AsyncMock:
    """Build a mock that mimics openai chat.completions.create()."""
    choice = AsyncMock()
    choice.message.content = content
    response = AsyncMock()
    response.choices = [choice]
    mock_create = AsyncMock(return_value=response)
    return mock_create


# --- Basic AI connectivity (Part 8) ---


@pytest.mark.anyio
async def test_ai_chat_function():
    """Test the ai.chat() wrapper calls the openai client correctly."""
    mock_create = _mock_completion("4")
    with patch("ai.client.chat.completions.create", mock_create):
        from ai import chat

        result = await chat([{"role": "user", "content": "What is 2+2?"}])
    assert result == "4"
    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args
    assert call_kwargs.kwargs["messages"] == [
        {"role": "user", "content": "What is 2+2?"}
    ]


@pytest.mark.anyio
async def test_ai_test_endpoint(client):
    """Test POST /api/ai/test returns the AI reply."""
    token = await login(client)
    mock_create = _mock_completion("2 + 2 equals 4.")
    with patch("ai.client.chat.completions.create", mock_create):
        res = await client.post("/api/ai/test", headers=auth_header(token))
    assert res.status_code == 200
    assert "4" in res.json()["reply"]


@pytest.mark.anyio
async def test_ai_test_requires_auth(client):
    """Test POST /api/ai/test requires authentication."""
    res = await client.post("/api/ai/test")
    assert res.status_code == 401


# --- Structured outputs (Part 9) ---


@pytest.mark.anyio
async def test_chat_with_board_includes_board_context():
    """Test that chat_with_board passes board state in the system prompt."""
    board = {"columns": [], "cards": {}}
    mock_create = _mock_completion(json.dumps({"message": "Hi", "board_update": None}))
    with patch("ai.client.chat.completions.create", mock_create):
        from ai import chat_with_board

        result = await chat_with_board("hello", [], board)
    assert result["message"] == "Hi"
    assert result["board_update"] is None
    # Verify board state was included in system message
    call_args = mock_create.call_args.kwargs["messages"]
    system_msg = call_args[0]
    assert system_msg["role"] == "system"
    assert '"columns": []' in system_msg["content"]


@pytest.mark.anyio
async def test_chat_with_board_passes_history():
    """Test that conversation history is included in the messages."""
    board = {"columns": [], "cards": {}}
    history = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "reply"},
    ]
    mock_create = _mock_completion(json.dumps({"message": "ok", "board_update": None}))
    with patch("ai.client.chat.completions.create", mock_create):
        from ai import chat_with_board

        await chat_with_board("second", history, board)
    call_args = mock_create.call_args.kwargs["messages"]
    # system + 2 history + 1 user = 4 messages
    assert len(call_args) == 4
    assert call_args[1] == {"role": "user", "content": "first"}
    assert call_args[2] == {"role": "assistant", "content": "reply"}
    assert call_args[3] == {"role": "user", "content": "second"}


@pytest.mark.anyio
async def test_chat_with_board_handles_invalid_json():
    """Test graceful handling when AI returns non-JSON."""
    board = {"columns": [], "cards": {}}
    mock_create = _mock_completion("I don't know how to format JSON")
    with patch("ai.client.chat.completions.create", mock_create):
        from ai import chat_with_board

        result = await chat_with_board("hello", [], board)
    assert result["message"] == "I don't know how to format JSON"
    assert result["board_update"] is None


@pytest.mark.anyio
async def test_chat_endpoint_no_board_update(client):
    """Test /api/ai/chat when AI returns null board_update -- DB unchanged."""
    token = await login(client)

    # Get initial board state
    res = await client.get("/api/board", headers=auth_header(token))
    initial_board = res.json()

    ai_response = json.dumps({"message": "Hello! How can I help?", "board_update": None})
    mock_create = _mock_completion(ai_response)
    with patch("ai.client.chat.completions.create", mock_create):
        res = await client.post(
            "/api/ai/chat",
            json={"message": "hi", "history": []},
            headers=auth_header(token),
        )
    assert res.status_code == 200
    data = res.json()
    assert data["message"] == "Hello! How can I help?"
    assert data["board_update"] is None

    # Board unchanged
    res = await client.get("/api/board", headers=auth_header(token))
    assert res.json() == initial_board


@pytest.mark.anyio
async def test_chat_endpoint_with_board_update(client):
    """Test /api/ai/chat when AI returns board_update -- DB is updated."""
    token = await login(client)

    # Get initial board to know column IDs
    res = await client.get("/api/board", headers=auth_header(token))
    initial = res.json()
    col_id = initial["columns"][0]["id"]

    # AI returns a board_update that adds a card
    updated_board = {
        "columns": initial["columns"].copy(),
        "cards": {"card-aaaa1111": {"id": "card-aaaa1111", "title": "AI Card", "details": "Created by AI"}},
    }
    updated_board["columns"][0] = {**updated_board["columns"][0], "cardIds": ["card-aaaa1111"]}

    ai_response = json.dumps({"message": "Done! I added a card.", "board_update": updated_board})
    mock_create = _mock_completion(ai_response)
    with patch("ai.client.chat.completions.create", mock_create):
        res = await client.post(
            "/api/ai/chat",
            json={"message": "Add a card to the first column", "history": []},
            headers=auth_header(token),
        )
    assert res.status_code == 200
    data = res.json()
    assert data["message"] == "Done! I added a card."
    assert data["board_update"] is not None

    # Verify card was persisted
    res = await client.get("/api/board", headers=auth_header(token))
    board = res.json()
    assert "card-aaaa1111" in board["cards"]
    assert board["cards"]["card-aaaa1111"]["title"] == "AI Card"


@pytest.mark.anyio
async def test_chat_endpoint_with_history(client):
    """Test that /api/ai/chat passes history to AI correctly."""
    token = await login(client)
    history = [
        {"role": "user", "content": "Create a task"},
        {"role": "assistant", "content": "Sure, what task?"},
    ]
    ai_response = json.dumps({"message": "Got it.", "board_update": None})
    mock_create = _mock_completion(ai_response)
    with patch("ai.client.chat.completions.create", mock_create):
        res = await client.post(
            "/api/ai/chat",
            json={"message": "A test task", "history": history},
            headers=auth_header(token),
        )
    assert res.status_code == 200
    # Verify history was passed through
    call_args = mock_create.call_args.kwargs["messages"]
    # system + 2 history + 1 user = 4
    assert len(call_args) == 4
    assert call_args[1]["content"] == "Create a task"
    assert call_args[2]["content"] == "Sure, what task?"
    assert call_args[3]["content"] == "A test task"


@pytest.mark.anyio
async def test_chat_endpoint_requires_auth(client):
    """Test POST /api/ai/chat requires authentication."""
    res = await client.post("/api/ai/chat", json={"message": "hi"})
    assert res.status_code == 401
