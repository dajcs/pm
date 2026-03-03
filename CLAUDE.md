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

### Frontend (`frontend/src/`)
- `app/page.tsx` — auth state gating; renders `LoginPage` or `KanbanBoard` + `ChatSidebar`
- `components/KanbanBoard.tsx` — top-level board, drag-and-drop via `@dnd-kit`
- `components/KanbanColumn.tsx` / `KanbanCard.tsx` — column and card rendering with inline editing
- `components/ChatSidebar.tsx` — AI chat; sends board context, applies `board_update` from AI response
- `lib/api.ts` — API client; attaches JWT `Bearer` token; auto-logouts on 401
- `lib/kanban.ts` — pure board state logic (move card, reorder columns, etc.)
- Path alias: `@/*` → `src/*`

### Backend (`backend/`)
- `main.py` — FastAPI app; all routes; serves static frontend at `/`
- `database.py` — SQLite schema (users, boards, columns, cards) and async CRUD
- `models.py` — Pydantic request/response models
- `auth.py` — JWT creation and validation (hardcoded creds: `user` / `password`)
- `ai.py` — OpenRouter chat; system prompt enforces structured JSON `{message, board_update}`

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
- Accent Yellow: `#ecad0a`
- Blue Primary: `#209dd7`
- Purple Secondary: `#753991`
- Dark Navy: `#032147`
- Gray Text: `#888888`
