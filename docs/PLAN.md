# Kanban Studio MVP -- Execution Plan

Full plan with detailed prompt: `.github/prompts/plan-kanbanStudioMvp.prompt.md`

---

## Part 1: Plan + Frontend AGENTS.md

- [x] Create frontend/AGENTS.md describing existing frontend code
- [x] Enrich docs/PLAN.md with full checklist plan
- [ ] User reviews and approves the plan

---

## Part 2: Scaffolding (Docker + FastAPI + Scripts)

- [ ] Create backend pyproject.toml with dependencies (fastapi, uvicorn, python-jose, aiosqlite, openai)
- [ ] Create backend/main.py with /api/health endpoint + static file serving
- [ ] Create Dockerfile (Python base, uv, build frontend, serve static)
- [ ] Create docker-compose.yml (port 8000, mount .env)
- [ ] Create scripts: start.sh, stop.sh, start.ps1, stop.ps1
- [ ] Create temporary static/index.html for hello world test
- [ ] Verify: hello world at localhost:8000, /api/health returns ok, stop script works

---

## Part 3: Serve the Frontend

- [ ] Set output: 'export' in next.config.ts
- [ ] Update Dockerfile to build frontend and copy static output
- [ ] Update backend to serve Next.js export at /
- [ ] Add inline card editing to KanbanCard.tsx
- [ ] Add handleEditCard to KanbanBoard.tsx
- [ ] Add unit tests for inline editing
- [ ] Verify: board at localhost:8000, all unit tests pass, cards editable inline

---

## Part 4: Fake Sign-in

- [ ] Add /api/auth/login POST endpoint (hardcoded user/password, returns JWT)
- [ ] Add /api/auth/me GET endpoint (validates JWT)
- [ ] Create backend/auth.py (create_token, verify_token)
- [ ] Create LoginPage frontend component
- [ ] Update page.tsx for auth flow (check token, show login or board)
- [ ] Add logout button to board header
- [ ] Add get_current_user dependency for protected routes
- [ ] Backend tests: login success/failure, token validation
- [ ] Frontend tests: LoginPage form, auth flow
- [ ] E2E test: login, see board, logout

---

## Part 5: Database Schema

- [ ] Create docs/database.md documenting schema
- [ ] Create docs/schema.json with schema definition
- [ ] Tables: users, boards, columns, cards
- [ ] User reviews and approves schema

---

## Part 6: Backend API

- [ ] Create backend/database.py with init_db() (creates tables, seeds user)
- [ ] Create backend/models.py (Pydantic models)
- [ ] Add routes: GET /api/board, PUT /api/board, POST/DELETE/PATCH cards, PATCH columns, PUT columns/order
- [ ] Call init_db() on app startup
- [ ] All endpoints require JWT auth
- [ ] Pytest tests: init_db, auth, CRUD, default board creation

---

## Part 7: Frontend + Backend Integration

- [ ] Create frontend/src/lib/api.ts (API client with JWT headers)
- [ ] Update KanbanBoard to fetch from API on mount
- [ ] Add loading state
- [ ] Wire all mutations to API (optimistic updates)
- [ ] Remove initialData from production code
- [ ] Handle API errors
- [ ] Frontend unit tests with mocked API
- [ ] E2E tests: persistence across refresh, drag-drop persists, inline edit persists

---

## Part 8: AI Connectivity

- [ ] Create backend/ai.py (OpenRouter wrapper via openai client)
- [ ] Add POST /api/ai/test endpoint (2+2 test)
- [ ] Load .env for API key
- [ ] Unit test with mocked API
- [ ] Verify: /api/ai/test returns response containing "4"

---

## Part 9: AI Structured Outputs

- [ ] Define structured output schema (message + optional board_update)
- [ ] Update AI call to include board state, history, user message
- [ ] Add POST /api/ai/chat endpoint
- [ ] System prompt for PM assistant role
- [ ] Tests: board context included, board_update saved/not-saved, history passed

---

## Part 10: AI Chat Sidebar

- [ ] Create ChatSidebar.tsx (always visible, scrollable messages, input)
- [ ] Create ChatMessage.tsx (message bubble with edit/delete for user messages)
- [ ] Update layout: board + sidebar side by side
- [ ] Chat state: useState for messages array (ephemeral)
- [ ] Edit message: clear subsequent, re-send to AI
- [ ] Delete message: remove it and all subsequent
- [ ] Auto-refetch board on board_update from AI
- [ ] Unit tests: send, edit, delete messages
- [ ] E2E tests: chat flow, AI board mutation
