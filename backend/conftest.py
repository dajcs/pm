"""Shared test fixtures for backend tests."""

import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

# Patch DB_PATH before importing app
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["KANBAN_TEST_DB"] = _tmp.name

import database  # noqa: E402

database.DB_PATH = type(database.DB_PATH)(_tmp.name)

from main import app  # noqa: E402


@pytest.fixture(autouse=True)
async def _reset_db():
    """Re-initialize the database before each test."""
    # Remove old DB and re-init
    db_path = database.get_db_path()
    if os.path.exists(db_path):
        os.unlink(db_path)
    await database.init_db()
    yield
    if os.path.exists(db_path):
        os.unlink(db_path)


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
