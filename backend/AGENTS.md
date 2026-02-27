# Backend: Kanban Studio API

Python FastAPI backend served via uvicorn.

## Structure

- `main.py` -- FastAPI app with `/api/health` endpoint, serves static files from `static/`
- `pyproject.toml` -- dependencies managed by `uv`
- `static/` -- temporary hello world page (replaced by frontend build in Part 3)

## Dependencies

fastapi, uvicorn, python-jose[cryptography], aiosqlite, openai, python-dotenv

## Running

Via Docker: `scripts/start.sh` or `docker compose up -d --build`
Direct: `cd backend && uvicorn main:app --port 8000`
