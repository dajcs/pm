"""Shared test fixtures for backend tests."""

import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

# Disable rate limiting in tests
os.environ["DISABLE_RATE_LIMIT"] = "true"

# Patch DB_PATH before importing app
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()

import database  # noqa: E402

database.DB_PATH = type(database.DB_PATH)(_tmp.name)

from main import app  # noqa: E402


@pytest.fixture(autouse=True)
async def _reset_db():
    """Re-initialize the database before each test using table drops (works on Windows)."""
    db = await database.get_db()
    try:
        await db.executescript("""
            DROP TABLE IF EXISTS activity_log;
            DROP TABLE IF EXISTS comments;
            DROP TABLE IF EXISTS checklist_items;
            DROP TABLE IF EXISTS cards;
            DROP TABLE IF EXISTS columns;
            DROP TABLE IF EXISTS boards;
            DROP TABLE IF EXISTS users;
        """)
        await db.commit()
    finally:
        await db.close()
    await database.init_db()
    yield


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def login(client: AsyncClient) -> str:
    """Helper: login and return the auth token."""
    res = await client.post(
        "/api/auth/login", json={"username": "user", "password": "password"}
    )
    return res.json()["token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
