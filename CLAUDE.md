# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Kanban Project Management MVP with:
- **Frontend:** Next.js 16 + React 19 + TypeScript + Tailwind CSS 4 (static export)
- **Backend:** Python FastAPI + SQLite (aiosqlite) + JWT auth
- **AI:** OpenRouter API (`openai/gpt-oss-120b:free`) via `OPENROUTER_API_KEY` in `.env`
- **Deployment:** Single Docker container; FastAPI serves the built Next.js static files at `/`

## Development Commands

### Frontend (`frontend/`)
```bash
npm run dev          # Dev server at http://localhost:3000
npm run build        # Static export (required for Docker)
npm run lint         # ESLint
npm run test:unit    # Vitest unit tests
npm run test:unit:watch  # Watch mode
npm run test:e2e     # Playwright E2E (requires server at http://127.0.0.1:3000)
npm run test:all     # Both unit and E2E
```

### Backend (`backend/`)
```bash
uvicorn main:app --reload    # Dev server at http://localhost:8000
pytest                       # All tests
pytest test_api.py -v        # Single test file, verbose
```

### Docker (production)
```bash
./scripts/start.sh    # Build and start (Linux/Mac); app at http://localhost:8000
./scripts/stop.sh     # Stop
# Windows: use scripts/start.ps1 / stop.ps1
```

## Architecture

### Data Model

Shared between frontend types and backend API contract:
```
Card      = { id: string, title: string, details: string }
Column    = { id: string, title: string, cardIds: string[] }
BoardData = { columns: Column[], cards: Record<string, Card> }
```
Cards stored in a flat map; columns reference cards by ID.

### Frontend (`frontend/src/`)
- `app/page.tsx` — auth state gating; renders `LoginPage` or `KanbanBoard` + `ChatSidebar`
- `components/KanbanBoard.tsx` — owns all board state (`useState<BoardData>`); drag-and-drop via `@dnd-kit`
- `components/KanbanColumn.tsx` / `KanbanCard.tsx` — column and card rendering with inline editing
- `components/ChatSidebar.tsx` — AI chat; sends board context, applies `board_update` from AI response
- `lib/api.ts` — API client; attaches JWT `Bearer` token; auto-logouts on 401
- `lib/kanban.ts` — pure board state logic (`moveCard`, `createId`); unit-tested in `lib/kanban.test.ts`
- Component tests: `components/KanbanBoard.test.tsx`, `LoginPage.test.tsx`, `ChatSidebar.test.tsx`
- Path alias: `@/*` → `src/*`
- Fonts: Space Grotesk (headings, `.font-display`) + Manrope (body, `--font-body`) via `next/font/google`

### Backend (`backend/`)
- `main.py` — FastAPI app; all routes; serves static frontend at `/`
- `database.py` — SQLite schema (users, boards, columns, cards) and async CRUD
- `models.py` — Pydantic request/response models
- `auth.py` — JWT creation and validation (hardcoded creds: `user` / `password`)
- `ai.py` — OpenRouter chat; system prompt enforces structured JSON `{message, board_update}`
- `conftest.py` — shared test fixtures; uses temp SQLite DB (`KANBAN_TEST_DB` env var); provides `client`, `login()`, and `auth_header()` helpers
- Test files: `test_api.py`, `test_auth.py`, `test_ai.py`; all async via `pytest-anyio` (`asyncio_mode = "auto"` in `pyproject.toml`)

### Key API Routes
```
POST /api/auth/login         # Returns JWT
GET  /api/board              # Load board state
PUT  /api/board              # Save full board state
POST /api/board/cards        # Create card
PATCH /api/board/cards/{id}  # Update card
DELETE /api/board/cards/{id} # Delete card
PATCH /api/board/columns/{id}       # Rename column
PUT  /api/board/columns/order       # Reorder columns
POST /api/ai/chat            # AI chat with board context
GET  /api/health             # Health check
```

### Database
SQLite at `/app/data/kanban.db` (Docker volume). Default columns: Backlog, To Do, Discovery, In Progress, Done.

## Coding Standards (from AGENTS.md)

- No over-engineering; no unnecessary defensive programming; no extra features
- No emojis, ever
- Keep README and documentation minimal
- When hitting issues: identify root cause first, prove with evidence, then fix

## Color Scheme

CSS custom properties in `globals.css`:
- `--accent-yellow: #ecad0a`
- `--primary-blue: #209dd7`
- `--secondary-purple: #753991`
- `--navy-dark: #032147`
- `--gray-text: #888888`
- `--surface: #f7f8fb` (page background)
- `--surface-strong: #ffffff`
- `--stroke: rgba(3,33,71,0.08)`
- `--shadow: 0 18px 40px rgba(3,33,71,0.12)`

## Reference Docs

`docs/` contains planning and schema references:
- `docs/PLAN.md` — original implementation plan
- `docs/database.md` — database schema notes
- `docs/schema.json` — AI response JSON schema
