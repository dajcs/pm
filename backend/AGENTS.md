# Backend: Kanban Studio API

Python FastAPI backend served via uvicorn.

## Structure

- `main.py` -- FastAPI app with auth, board CRUD, card/column endpoints. Lifespan calls `init_db()`. Static files served last.
- `auth.py` -- JWT utilities: `create_token()`, `verify_token()`. Hardcoded credentials (`user`/`password`).
- `database.py` -- SQLite via `aiosqlite`. `init_db()` creates tables + seeds user. CRUD functions for boards, cards, columns.
- `models.py` -- Pydantic models: `Card`, `Column`, `BoardData`, request models.
- `pyproject.toml` -- dependencies managed by `uv`
- `conftest.py` -- shared pytest fixtures (temp DB, auto-reset, client, login helper)
- `test_auth.py` -- auth endpoint tests (6 tests)
- `test_api.py` -- full API tests: init_db, board CRUD, card CRUD, column rename, reorder (15 tests)
- `static/` -- frontend build output (copied in Docker)

## API Endpoints

- `GET /api/health` -- health check
- `POST /api/auth/login` -- returns JWT token
- `GET /api/auth/me` -- validates token, returns username
- `GET /api/board` -- returns full board (auto-creates default if none)
- `PUT /api/board` -- replaces entire board
- `POST /api/board/cards` -- create a card
- `DELETE /api/board/cards/{card_id}` -- delete a card
- `PATCH /api/board/cards/{card_id}` -- update card title/details
- `PATCH /api/board/columns/{column_id}` -- rename a column
- `PUT /api/board/columns/order` -- reorder columns/cards (full board replace)

## Dependencies

fastapi, uvicorn, python-jose[cryptography], aiosqlite, openai, python-dotenv

## Running

Via Docker: `scripts/start.sh` or `docker compose up -d --build`
Direct: `cd backend && uvicorn main:app --port 8000`
Tests: `cd backend && python3 -m pytest -v`
