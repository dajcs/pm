"""Tests for the AI connectivity module."""

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
