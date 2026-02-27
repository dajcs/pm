# Plan: Kanban Studio MVP (10 Parts)

**TL;DR:** Build a full-stack Kanban app with a Next.js static frontend served by a Python FastAPI backend in Docker. JWT auth with hardcoded credentials, SQLite persistence, and an always-visible AI chat sidebar powered by OpenRouter. The frontend demo already exists with drag-and-drop, column rename, and card create/delete. We'll add inline card editing, wire up the backend API, add auth, and integrate AI chat with structured outputs that can mutate the board.

---

## Part 1: Plan + Frontend AGENTS.md

**Steps**
1. Create frontend/AGENTS.md describing the existing frontend: component tree, data model (`Card`, `Column`, `BoardData`), state management (React `useState`), drag-and-drop (`@dnd-kit`), styling (Tailwind v4 + CSS vars), fonts (Space Grotesk + Manrope), test setup (Vitest + Playwright)
2. Enrich docs/PLAN.md with this full checklist plan, including substeps and success criteria for each part

**Verification:** User reviews and approves the plan.

---

## Part 2: Scaffolding (Docker + FastAPI + Scripts)

**Steps**
1. Create backend/requirements.txt (or `pyproject.toml` for `uv`) with `fastapi`, `uvicorn`, `python-jose[cryptography]` (JWT), `aiosqlite`, `openai` (OpenRouter-compatible)
2. Create backend/main.py with a minimal FastAPI app: a `/api/health` endpoint returning `{"status": "ok"}` and static file serving from a `static/` directory
3. Create Dockerfile in project root: Python base image, install `uv`, copy backend, build frontend (`npm run build` + `next export` or `output: 'export'`), copy static output to backend's static dir, expose port 8000, run `uvicorn`
4. Create docker-compose.yml mapping port 8000 and mounting `.env`
5. Create start/stop scripts in scripts/: `start.sh` / `stop.sh` (Linux/Mac) and `start.ps1` / `stop.ps1` (Windows) -- these run `docker compose up -d` / `docker compose down`
6. Create a temporary `static/index.html` with "Hello World" for initial testing

**Verification**
- Run `scripts/start.sh`, open `http://localhost:8000` -- see "Hello World"
- Hit `http://localhost:8000/api/health` -- get `{"status": "ok"}`
- Run `scripts/stop.sh` -- container stops

---

## Part 3: Serve the Frontend

**Steps**
1. Update frontend/next.config.ts to set `output: 'export'` for static HTML generation
2. Update the Dockerfile build stage to run `npm run build` in `frontend/`, then copy `frontend/out/` to backend's static serving directory
3. Update backend/main.py to serve the static Next.js export at `/` using `StaticFiles` with `html=True`
4. Add inline card editing to KanbanCard.tsx: clicking title or details makes them editable inputs; blur or Enter saves; propagate `onEditCard(cardId, title, details)` up to `KanbanBoard`
5. Add `handleEditCard` to KanbanBoard.tsx that updates `board.cards[cardId]`
6. Ensure all existing unit tests still pass and add new tests:
   - Unit test for inline editing in `KanbanCard` (click title, type, blur -- verify change)
   - Unit test for `handleEditCard` in `KanbanBoard`
7. Update Playwright E2E test to verify the board loads at `http://localhost:8000`

**Verification**
- `npm run test:unit` in frontend -- all pass
- Docker container serves the Kanban board at `http://localhost:8000/`
- Cards can be edited inline

---

## Part 4: Fake Sign-in

**Steps**
1. Add `/api/auth/login` POST endpoint in backend/main.py: accepts `{"username": "user", "password": "password"}`, returns `{"token": "<jwt>"}`. Reject anything else with 401
2. Add `/api/auth/me` GET endpoint: validates JWT from `Authorization: Bearer <token>` header, returns `{"username": "user"}`
3. Add a JWT utility module backend/auth.py with `create_token(username)` and `verify_token(token)` using `python-jose`. Use a hardcoded secret key (fine for local MVP)
4. Create a `LoginPage` component in frontend/src/components/LoginPage.tsx: username + password form, styled with the existing design system, calls `/api/auth/login`, stores JWT in `localStorage`
5. Update frontend/src/app/page.tsx (or create an auth context): check for token in `localStorage`, validate via `/api/auth/me`, show `LoginPage` if invalid, show `KanbanBoard` if valid
6. Add a "Log out" button to the board header that clears the token and returns to login
7. Protect all future `/api/*` endpoints with a `get_current_user` dependency that validates the JWT

**Tests**
- Backend unit test: login with correct creds returns JWT; wrong creds returns 401; `/api/auth/me` with valid token returns user; invalid token returns 401
- Frontend unit test: `LoginPage` renders form, submits, calls API
- E2E test: visit `/`, see login form, enter credentials, see Kanban board, log out, see login form again

**Verification**
- Cannot see the board without logging in
- After login, board is displayed with full functionality
- Logout returns to login screen

---

## Part 5: Database Schema

**Steps**
1. Create docs/database.md documenting the schema
2. Create docs/schema.json with the schema definition

**Proposed schema (SQLite):**

- **users** table: `id` (INTEGER PK), `username` (TEXT UNIQUE), `password_hash` (TEXT)
- **boards** table: `id` (INTEGER PK), `user_id` (INTEGER FK -> users), `name` (TEXT), `created_at` (TEXT ISO8601)
- **columns** table: `id` (TEXT PK, e.g. "col-backlog"), `board_id` (INTEGER FK -> boards), `title` (TEXT), `position` (INTEGER) -- ordering
- **cards** table: `id` (TEXT PK, e.g. "card-xyz"), `column_id` (TEXT FK -> columns), `title` (TEXT), `details` (TEXT), `position` (INTEGER) -- ordering within column

Notes: Position integers handle ordering. No `board_id` on cards since it's derived through the column. Single user for MVP but schema supports multiple. Password stored as hash even for hardcoded creds.

**Verification:** User reviews and approves the schema.

---

## Part 6: Backend API

**Steps**
1. Create backend/database.py: `init_db()` creates SQLite file + tables if not exist, seeds default user (`user` / hashed `password`). Use `aiosqlite` for async
2. Create backend/models.py: Pydantic models mirroring the frontend types -- `Card`, `Column`, `BoardData`, plus request/response models
3. Add API routes to backend/main.py (or a separate router file):
   - `GET /api/board` -- returns `BoardData` JSON for the authenticated user (create default board if none exists)
   - `PUT /api/board` -- accepts full `BoardData` JSON, replaces the user's board (simplest approach: delete all columns/cards, re-insert)
   - `POST /api/board/cards` -- create a card in a specified column
   - `DELETE /api/board/cards/{card_id}` -- delete a card
   - `PATCH /api/board/cards/{card_id}` -- update card title/details
   - `PATCH /api/board/columns/{column_id}` -- rename a column
   - `PUT /api/board/columns/order` -- reorder (for drag-and-drop: accepts full column+cardId arrays)
4. Call `init_db()` on app startup via FastAPI lifespan
5. All endpoints require JWT auth via the `get_current_user` dependency

**Tests** (pytest)
- Test `init_db` creates tables and seeds user
- Test each API endpoint with valid/invalid auth
- Test CRUD operations: create card, read board, update card, delete card, rename column, reorder
- Test that a new user gets a default board created automatically

**Verification**
- `pytest` passes all backend tests
- Manual curl/httpie calls to each endpoint return correct data
- Database file created automatically on first run

---

## Part 7: Frontend + Backend Integration

**Steps**
1. Create frontend/src/lib/api.ts: API client module with functions for each endpoint. Include JWT token in headers. Handle 401 by redirecting to login
2. Update `KanbanBoard` to:
   - Fetch board data on mount via `GET /api/board` instead of using `initialData`
   - Show a loading state while fetching
   - On every mutation (add/edit/delete card, rename column, drag-drop), call the corresponding API endpoint, then update local state optimistically (or refetch)
3. Strategy for drag-and-drop sync: after `handleDragEnd`, call `PUT /api/board/columns/order` with the new column arrangement. Use optimistic updates (update state immediately, roll back on error)
4. Remove `initialData` usage from production code (keep for tests)
5. Handle API errors gracefully: show a toast/banner on failure

**Tests**
- Frontend unit tests: mock API calls, verify `KanbanBoard` fetches on mount, updates on mutations
- E2E test: full flow -- login, see board loaded from DB, add a card, refresh page, card persists, drag card, refresh, new position persists
- E2E test: edit a card inline, refresh, changes persist

**Verification**
- All changes persist across page refreshes
- Drag-and-drop persists card positions
- Board loads from the database, not from hardcoded initial data

---

## Part 8: AI Connectivity

**Steps**
1. Create backend/ai.py: wrapper around OpenRouter API using the `openai` Python client with `base_url="https://openrouter.ai/api/v1"` and `api_key` from `.env`
2. Add `POST /api/ai/test` endpoint: sends "What is 2+2?" to `openai/gpt-oss-120b:free`, returns the response
3. Load `.env` via `python-dotenv` or FastAPI settings

**Tests**
- Unit test with mocked API: verify request format and response parsing
- Integration test (can be skipped in CI): call the real endpoint, verify non-empty response

**Verification**
- Hit `/api/ai/test` and get a response containing "4"

---

## Part 9: AI Structured Outputs

**Steps**
1. Define structured output schema in backend/ai.py:
   ```
   Response = {
     "message": string,          // AI's text reply to the user
     "board_update": BoardData | null  // optional full board state replacement
   }
   ```
2. Update the AI call to:
   - Include the current board state as JSON in the system prompt
   - Include conversation history (list of `{role, content}` messages)
   - Include the user's new message
   - Request structured JSON output matching the schema
3. Add `POST /api/ai/chat` endpoint: accepts `{"message": string, "history": [{role, content}...]}`, fetches current board from DB, calls AI, if `board_update` is non-null saves it to DB, returns the full AI response
4. The system prompt should instruct the AI: "You are a project management assistant. You can view and modify the user's Kanban board. When the user asks you to create, move, edit, or delete cards, return the updated board state in `board_update`. Otherwise set `board_update` to null."

**Tests**
- Unit test with mocked AI: send a message, verify board context is included, verify response parsing
- Unit test: when AI returns `board_update`, verify it's saved to DB
- Unit test: when AI returns null `board_update`, verify DB unchanged
- Test conversation history is passed correctly

**Verification**
- Chat endpoint returns AI responses
- AI can modify the board (verified via subsequent `GET /api/board`)

---

## Part 10: AI Chat Sidebar

**Steps**
1. Create frontend/src/components/ChatSidebar.tsx: always-visible panel on the right side of the screen
   - Chat message list (scrollable)
   - Input field at the bottom with send button
   - Each message shows role (user/assistant) with appropriate styling
   - User messages have edit/delete buttons
   - Editing a message clears all subsequent messages and re-sends to AI
   - Deleting a message removes it and all subsequent messages
2. Create frontend/src/components/ChatMessage.tsx: individual message bubble with edit/delete controls for user messages
3. Update page layout: split into two columns -- Kanban board (left, flex-grow) + chat sidebar (right, fixed width ~350px). The sidebar is always visible when signed in
4. Chat state management: `useState` for `messages` array in a parent component (or lift to page level). Messages are `{id, role, content}[]`
5. When AI response includes `board_update`, automatically refetch the board data to reflect changes. Show a subtle indicator that the board was updated
6. Style the sidebar consistent with the existing design system: same fonts, colors, border radius, shadows

**Tests**
- Unit test: `ChatSidebar` renders, user can type and send messages
- Unit test: editing a user message clears later messages
- Unit test: deleting a message removes it and subsequent messages
- E2E test: send a chat message, receive AI response
- E2E test: ask AI to create a card, verify it appears on the board

**Verification**
- Chat sidebar always visible alongside the board
- Messages display correctly with role indicators
- User can edit/delete their messages (editing re-triggers AI from that point)
- AI responses that modify the board cause the board UI to update immediately
- Full conversation flow works end-to-end

---

## Key Decisions

- **Card editing:** Inline (click to edit in-place), not modal
- **Auth:** JWT tokens in `Authorization` header, stored in `localStorage`
- **Chat history:** Ephemeral (frontend state only, lost on refresh). Editing a message clears all subsequent messages and re-sends
- **AI sidebar:** Always visible when signed in (not toggleable)
- **Database:** Raw SQL with `aiosqlite` (no ORM -- keeps it simple per coding standards)
- **Board sync strategy:** `PUT /api/board` for full board replacement on drag-drop; granular endpoints for individual card/column operations
- **Static export:** Next.js `output: 'export'` for static HTML served by FastAPI
