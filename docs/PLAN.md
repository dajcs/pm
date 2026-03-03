# Kanban Studio MVP -- Execution Plan

Full plan with detailed prompt: `.github/prompts/plan-kanbanStudioMvp.prompt.md`

---

## Part 1: Plan + Frontend AGENTS.md

- [x] Create frontend/AGENTS.md describing existing frontend code
- [x] Enrich docs/PLAN.md with full checklist plan
- [x] User reviews and approves the plan

---

## Part 2: Scaffolding (Docker + FastAPI + Scripts)

- [x] Create backend pyproject.toml with dependencies (fastapi, uvicorn, python-jose, aiosqlite, openai)
- [x] Create backend/main.py with /api/health endpoint + static file serving
- [x] Create Dockerfile (Python base, uv, build frontend, serve static)
- [x] Create docker-compose.yml (port 8000, mount .env)
- [x] Create scripts: start.sh, stop.sh, start.ps1, stop.ps1
- [x] Create temporary static/index.html for hello world test
- [x] Verify: hello world at localhost:8000, /api/health returns ok, stop script works

---

## Part 3: Serve the Frontend

- [x] Set output: 'export' in next.config.ts
- [x] Update Dockerfile to build frontend and copy static output
- [x] Update backend to serve Next.js export at /
- [x] Add inline card editing to KanbanCard.tsx
- [x] Add handleEditCard to KanbanBoard.tsx
- [x] Add unit tests for inline editing
- [x] Verify: board at localhost:8000, all unit tests pass, cards editable inline

---

## Part 4: Fake Sign-in

- [x] Add /api/auth/login POST endpoint (hardcoded user/password, returns JWT)
- [x] Add /api/auth/me GET endpoint (validates JWT)
- [x] Create backend/auth.py (create_token, verify_token)
- [x] Create LoginPage frontend component
- [x] Update page.tsx for auth flow (check token, show login or board)
- [x] Add logout button to board header
- [x] Add get_current_user dependency for protected routes
- [x] Backend tests: login success/failure, token validation
- [x] Frontend tests: LoginPage form, auth flow
- [x] E2E test: login, see board, logout

---

## Part 5: Database Schema

- [x] Create docs/database.md documenting schema
- [x] Create docs/schema.json with schema definition
- [x] Tables: users, boards, columns, cards
- [x] User reviews and approves schema

---

## Part 6: Backend API

- [x] Create backend/database.py with init_db() (creates tables, seeds user)
- [x] Create backend/models.py (Pydantic models)
- [x] Add routes: GET /api/board, PUT /api/board, POST/DELETE/PATCH cards, PATCH columns, PUT columns/order
- [x] Call init_db() on app startup
- [x] All endpoints require JWT auth
- [x] Pytest tests: init_db, auth, CRUD, default board creation

---

## Part 7: Frontend + Backend Integration

- [x] Create frontend/src/lib/api.ts (API client with JWT headers)
- [x] Update KanbanBoard to fetch from API on mount
- [x] Add loading state
- [x] Wire all mutations to API (optimistic updates)
- [x] Remove initialData from production code
- [x] Handle API errors (toast + 401 auto-logout)
- [x] Frontend unit tests with mocked API
- [x] E2E tests: persistence across refresh, drag-drop persists, inline edit persists

---

## Part 8: AI Connectivity

- [x] Create backend/ai.py (OpenRouter wrapper via openai client)
- [x] Add POST /api/ai/test endpoint (2+2 test)
- [x] Load .env for API key
- [x] Unit test with mocked API
- [x] Verify: /api/ai/test returns response containing "4"

---

## Part 9: AI Structured Outputs

- [x] Define structured output schema (message + optional board_update)
- [x] Update AI call to include board state, history, user message
- [x] Add POST /api/ai/chat endpoint
- [x] System prompt for PM assistant role
- [x] Tests: board context included, board_update saved/not-saved, history passed

---

## Part 10: AI Chat Sidebar

- [x] Create ChatSidebar.tsx (always visible, scrollable messages, input)
- [x] Create ChatMessage.tsx (message bubble with edit/delete for user messages)
- [x] Update layout: board + sidebar side by side
- [x] Chat state: useState for messages array (ephemeral)
- [x] Edit message: clear subsequent, re-send to AI
- [x] Delete message: remove it and all subsequent
- [x] Auto-refetch board on board_update from AI
- [x] Unit tests: send, edit, delete messages (7 tests)
- [x] E2E tests: chat flow, AI board mutation
