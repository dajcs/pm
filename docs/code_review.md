# Kanban Studio MVP — Comprehensive Code Review

**Date:** 2026-03-02
**Scope:** Full stack (backend Python/FastAPI + frontend Next.js/React) + infrastructure

---

## 1. Security

### SEC-1 — CRITICAL: Hardcoded credentials and JWT secret in source code
**File:** `backend/auth.py`, lines 5, 9–10

```python
SECRET_KEY = "kanban-studio-dev-secret-key"
VALID_USERNAME = "user"
VALID_PASSWORD = "password"
```

All three values are committed to source control. Anyone with repo access can forge valid JWTs and the credentials are trivially guessable. Survivable only if the repo is private and the app is never internet-exposed; must be fixed before any public deployment.

**Action:** Move all three to environment variables (`SECRET_KEY`, `APP_USERNAME`, `APP_PASSWORD`). Use `os.environ.get()` and fail fast at startup if absent. Add `.env.example` with placeholder values.

---

### SEC-2 — HIGH: No input length / content validation on Pydantic models
**File:** `backend/models.py`

`Card.title`, `Card.details`, `Column.title`, `ChatMessage.content`, and `ChatRequest.message` accept arbitrarily long strings. This allows unbounded DB row sizes and allows an attacker to push arbitrarily large AI prompts through `/api/ai/chat`, potentially exhausting the OpenRouter quota.

**Action:** Add `Field(max_length=...)` to all string fields. Practical limits: title=200, details=4000, chat message=2000.

---

### SEC-3 — HIGH: Bare `except Exception` silently swallows AI board validation errors
**File:** `backend/main.py`, lines 227–229

```python
except Exception:
    result["board_update"] = None
```

A `BoardData.model_validate()` failure is dropped silently with no logging. Scope the exception and add logging.

**Action:** Catch `ValidationError` specifically and log the exception (`logger.warning("board_update validation failed", exc_info=True)`).

---

### SEC-4 — HIGH: SHA-256 password hashing without a salt
**File:** `backend/database.py`, line 20

```python
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()
```

SHA-256 with no salt is GPU-crackable and vulnerable to rainbow tables. The stored hash for `"password"` is a constant value, instantly reversible via lookup.

**Action:** Replace with `bcrypt` or `argon2-cffi`.

---

### SEC-5 — MEDIUM: No CORS configuration
**File:** `backend/main.py` (absent)

No `CORSMiddleware` is configured. Fine in the Docker deployment (same origin), but during development the frontend (port 3000) and backend (port 8000) are different origins, causing silent browser blocks.

**Action:** Add `CORSMiddleware` with `allow_origins=["http://localhost:3000"]` for development.

---

### SEC-6 — MEDIUM: JWT token stored in localStorage
**File:** `frontend/src/app/page.tsx:15,26`; `frontend/src/lib/api.ts:10`

`localStorage` is accessible to any JavaScript on the page. Third-party scripts (npm packages) could exfiltrate the token.

**Action:** Acceptable for MVP; document the risk. Long-term fix: `httpOnly` cookies.

---

### SEC-7 — MEDIUM: No rate limiting on `/api/auth/login` or `/api/ai/chat`
**File:** `backend/main.py` (absent)

The login endpoint has no brute-force protection. The AI chat endpoint can be abused to exhaust the OpenRouter API key quota.

**Action:** Add `slowapi` rate limiting — e.g. 5/minute per IP on login, 30/minute per user on AI chat.

---

### SEC-8 — LOW: No `.env.example` file
**File:** repo root

`.env` is gitignored but there is no `.env.example` documenting required variables.

**Action:** Add `.env.example` with `OPENROUTER_API_KEY=your_key_here` (and `SECRET_KEY`, `APP_USERNAME`, `APP_PASSWORD` once SEC-1 is fixed).

---

## 2. Correctness / Bugs

### BUG-1 — HIGH: Column rename fires an API request on every keystroke
**File:** `frontend/src/components/KanbanColumn.tsx:48`; `frontend/src/components/KanbanBoard.tsx:130`

```tsx
onChange={(event) => onRename(column.id, event.target.value)}
```

`handleRenameColumn` calls `api.renameColumn(...)` on every `onChange` event. Typing a 16-character name triggers 16 consecutive PATCH requests. If any intermediate one fails, the board state rolls back mid-type.

**Action:** Debounce the API call (300–500 ms), or switch to a commit-on-blur pattern like `KanbanCard` already uses.

---

### BUG-2 — HIGH: `board.cards[cardId]` can be `undefined` at render time
**File:** `frontend/src/components/KanbanBoard.tsx:288`

```tsx
cards={column.cardIds.map((cardId) => board.cards[cardId])}
```

If `column.cardIds` references an ID not in `board.cards` (due to an optimistic update desync or malformed server response), this produces an array containing `undefined`, causing a runtime crash.

**Action:** Filter: `column.cardIds.map((id) => board.cards[id]).filter(Boolean)`, or add a nullability guard inside `KanbanCard`.

---

### BUG-3 — HIGH: New DB connection opened per sub-operation
**File:** `backend/database.py:27–32`; `backend/main.py:111–123,135–146,156–167,180–191`

Every ownership check inside a request handler opens a new `aiosqlite.Connection` in addition to the one opened inside the database function it calls. A typical authenticated request opens/closes the DB 2–3 times.

**Action:** Consolidate to a single connection per request via FastAPI dependency injection (`Depends`). Also set `PRAGMA journal_mode=WAL` in `init_db` for concurrent access.

---

### BUG-4 — MEDIUM: `PUT /api/board` and `PUT /api/board/columns/order` are identical
**File:** `backend/main.py:98–101` and `197–200`

Both endpoints have identical bodies and accept identical `BoardData` payloads. The frontend also has two functions (`saveBoard`, `saveColumnsOrder`) calling different URLs that do the same thing.

**Action:** Remove one endpoint (or consolidate the frontend to always call `PUT /api/board`).

---

### BUG-5 — MEDIUM: `save_board` relies on implicit rollback on partial write failure
**File:** `backend/database.py:155–177`

`save_board` deletes all columns (cascading cards) then re-inserts in a loop. If the process crashes mid-loop, the board is left empty. Rollback relies on SQLite's implicit behaviour on unclosed transactions.

**Action:** Wrap the body in `async with db:` (auto-commits on success, auto-rolls back on exception), or explicitly call `await db.rollback()` in an `except` block.

---

### BUG-6 — MEDIUM: `initialData` fixture mismatches backend column IDs
**File:** `frontend/src/lib/kanban.ts:18–72`

`initialData` contains `col-review` (from the original frontend demo), but the backend's default columns use `col-todo` instead. If this data ever reaches a real board component it references column IDs the server does not know about.

**Action:** Move `initialData` to `src/test/fixtures.ts` so it is only imported by test files.

---

### BUG-7 — MEDIUM: `conftest.py` test isolation via file delete is fragile on Windows
**File:** `backend/conftest.py:22–31`

The `_reset_db` fixture deletes the SQLite file and calls `init_db()` before each test. If a test leaves a connection open, `os.unlink` will fail with `PermissionError` on Windows.

**Action:** Use `aiosqlite.connect(":memory:")` patched via `get_db_path`, or wrap each test in a transaction that is rolled back afterwards.

---

### BUG-8 — LOW: `createId` is dead code
**File:** `frontend/src/lib/kanban.ts:164–168`

`createId` is exported but never imported anywhere. Card IDs are generated server-side.

**Action:** Remove `createId`.

---

### BUG-9 — LOW: Imports inside function bodies
**File:** `backend/main.py:125`

```python
import uuid
card_id = f"card-{uuid.uuid4().hex[:8]}"
```

`import uuid` and several `from database import get_db` calls are placed inside function bodies.

**Action:** Move all imports to the top of the module.

---

### BUG-10 — LOW: `KANBAN_TEST_DB` environment variable is set but never read
**File:** `backend/conftest.py:12`

```python
os.environ["KANBAN_TEST_DB"] = _tmp.name
```

This variable is set but `database.py` overrides the path directly on the next line. The env var is misleading dead code.

**Action:** Remove the `os.environ["KANBAN_TEST_DB"]` line.

---

## 3. Test Coverage

### TST-1 — Good: Backend API coverage is solid
`test_api.py` covers create/read/update/delete for cards and columns including auth guards and 404 cases. `test_auth.py` covers login and token validation. `test_ai.py` covers the AI wrapper, structured output parsing, and the `/api/ai/chat` endpoint with mocked completions. Critical paths appear well covered.

---

### TST-2 — HIGH: No tests for optimistic update rollback on API failure
**File:** `frontend/src/components/KanbanBoard.test.tsx`

`handleDeleteCard`, `handleEditCard`, and `handleRenameColumn` all optimistically update state then roll back on API failure. No test verifies the board reverts when the API rejects.

**Action:** Add tests where `api.deleteCard` / `api.updateCard` / `api.renameColumn` reject, asserting the board state returns to its previous value.

---

### TST-3 — MEDIUM: No unit test for `handleDragEnd` integration
**File:** `frontend/src/components/KanbanBoard.test.tsx`

The E2E test covers a basic mouse-drag. There is no unit test for `handleDragEnd` → `moveCard` → `setBoard` → `api.saveColumnsOrder`. The custom collision detection makes regressions harder to catch.

**Action:** Add a unit test that fires a mock `DragEndEvent` and asserts the column state updates correctly.

---

### TST-4 — MEDIUM: No test for `save_board` partial write failure
**File:** `backend/test_api.py`

The delete-all-then-re-insert in `save_board` has no test covering what happens when an insert fails halfway through.

**Action:** Add a test that causes `save_board` to fail mid-insert (e.g. by passing a malformed card) and asserts the board is not left in a corrupt empty state.

---

### TST-5 — MEDIUM: `moveCard` edge cases not tested
**File:** `frontend/src/lib/kanban.test.ts`

Only three cases are tested. Missing: moving to the same position (no-op), moving the only card in a column, moving to an empty column via column ID, `activeId === overId` guard.

**Action:** Add the missing edge case tests.

---

### TST-6 — MEDIUM: Only Chromium tested in E2E
**File:** `frontend/playwright.config.ts:19–23`

Only `Desktop Chrome` is configured. `@dnd-kit` has pointer-event handling differences across browsers.

**Action:** Add `firefox` and `webkit` projects to `playwright.config.ts`.

---

### TST-7 — INFO: `asyncio_mode = "auto"` targets the wrong library
**File:** `backend/pyproject.toml:24`

`asyncio_mode = "auto"` is a `pytest-asyncio` setting, but the project uses `pytest-anyio`. The key is silently ignored.

**Action:** Remove `asyncio_mode = "auto"` from `[tool.pytest.ini_options]`.

---

## 4. Code Quality

### QUA-1 — MEDIUM: Ownership-check pattern repeated four times
**File:** `backend/main.py:111–123,135–146,156–167,180–191`

The pattern — open connection, `SELECT ... WHERE id = ? AND board_id = ?`, check `fetchone()`, close — is copy-pasted four times with only the SQL changing.

**Action:** Extract `async def verify_belongs_to_board(entity_table, entity_id, board_id)` that raises `HTTPException(404)` if not found.

---

### QUA-2 — MEDIUM: Module-level mutable state for ID counter in `ChatSidebar`
**File:** `frontend/src/components/ChatSidebar.tsx:12–19`

```ts
let nextId = 1;
export function resetIdCounter() { nextId = 1; }
```

A module-level counter persists across hot-reloads and between instances. The exported `resetIdCounter` exists solely for test cleanup, which is a code smell.

**Action:** Use `crypto.randomUUID()` (available in all modern browsers) to eliminate the counter and the export entirely.

---

### QUA-3 — MEDIUM: Card edit always commits both fields even when only one changed
**File:** `frontend/src/components/KanbanCard.tsx:31–38`

`commitEdit` always sends both `title` and `details` to the API regardless of which field changed.

**Action:** Track which field was edited and send only that field.

---

### QUA-4 — LOW: `LoginRequest` defined in `main.py` instead of `models.py`
**File:** `backend/main.py:35–37`

All other request models live in `models.py`.

**Action:** Move `LoginRequest` to `models.py`.

---

### QUA-5 — LOW: `ai_chat` import alias is only used once
**File:** `backend/main.py:9`

```python
from ai import chat as ai_chat, chat_with_board
```

`ai_chat` alias adds no clarity. Consider dropping it or removing the `/api/ai/test` endpoint.

---

### QUA-6 — LOW: Drag event handlers not memoized inconsistently
**File:** `frontend/src/components/KanbanBoard.tsx:88–97`

`handleDragStart` and `handleDragOver` are not wrapped in `useCallback` while `findColumnForItem` (their dependency) is. This causes unnecessary `DndContext` re-renders.

**Action:** Wrap `handleDragStart` and `handleDragOver` in `useCallback`.

---

### QUA-7 — LOW: Enter key commits the details textarea with no Shift+Enter support
**File:** `frontend/src/components/KanbanCard.tsx:40–43`

Pressing Enter in the details field commits immediately; there is no way to type a newline.

**Action:** Check `e.key === "Enter" && !e.shiftKey` for the textarea so Shift+Enter inserts a newline.

---

## 5. Performance

### PERF-1 — HIGH: N+1 queries in `load_board`
**File:** `backend/database.py:124–152`

```python
for col in cols:
    card_rows = await db.execute_fetchall(
        "SELECT ... FROM cards WHERE column_id = ? ORDER BY position", (col_id,)
    )
```

5 columns = 6 queries (1 + one per column). `load_board` is also called at the end of every mutation endpoint, multiplying the cost.

**Action:** Fetch all cards for the board in a single JOIN query and group in Python:
```sql
SELECT cards.* FROM cards
JOIN columns ON cards.column_id = columns.id
WHERE columns.board_id = ?
ORDER BY columns.position, cards.position
```

---

### PERF-2 — MEDIUM: No indexes on foreign key columns
**File:** `backend/database.py:38–63`

SQLite does not automatically index foreign key columns. Queries on `boards.user_id`, `columns.board_id`, and `cards.column_id` do full table scans.

**Action:** Add to `init_db`:
```sql
CREATE INDEX IF NOT EXISTS idx_boards_user_id ON boards(user_id);
CREATE INDEX IF NOT EXISTS idx_columns_board_id ON columns(board_id);
CREATE INDEX IF NOT EXISTS idx_cards_column_id ON cards(column_id);
```

---

### PERF-3 — MEDIUM: Full board JSON with `indent=2` sent to AI on every message
**File:** `backend/ai.py:72`

```python
system_content = SYSTEM_PROMPT + json.dumps(board_state, indent=2)
```

The full board is pretty-printed and included in the system prompt on every chat turn, regardless of whether the user is asking a board-related question.

**Action:** Use `separators=(',', ':')` to remove whitespace. Consider sending only column names + card counts unless a mutation is detected in the request.

---

### PERF-4 — LOW: `useMemo` on object reference always re-runs
**File:** `frontend/src/components/KanbanBoard.tsx:75`

```ts
const cardsById = useMemo(() => board?.cards ?? {}, [board?.cards]);
```

`board.cards` is always a new object reference when `setBoard` replaces the board. The memo never hits its cache.

**Action:** Remove the memo and use `board?.cards ?? {}` inline, or depend on `board` directly.

---

## 6. Architecture

### ARCH-1 — MEDIUM: `save_board` does a full delete-and-replace
**File:** `backend/database.py:155–177`

The entire board is deleted and re-inserted on every drag-drop. Concurrent sessions (two browser tabs) silently clobber each other via last-write-wins.

**Note:** Acceptable for MVP. Document the constraint. Targeted `PATCH` endpoints already exist for cards and columns but are bypassed for drag-drop.

---

### ARCH-2 — MEDIUM: Board refresh on AI update uses full `KanbanBoard` remount
**File:** `frontend/src/app/page.tsx:46–48,57`

```tsx
<KanbanBoard key={boardKey} onLogout={handleLogout} />
```

Incrementing `boardKey` unmounts and remounts `KanbanBoard` entirely, discarding all local UI state (open forms, edit states, error timers).

**Action:** Pass the `board_update` payload directly from `ChatSidebar` to `KanbanBoard` via a prop or callback so `setBoard` can be called in place.

---

### ARCH-3 — LOW: Fixture data ships in the production bundle
**File:** `frontend/src/lib/kanban.ts:18–72`

A 50-line hardcoded dataset with 8 fictional cards is exported from the production library module. It is only used by tests.

**Action:** Move to `src/test/fixtures.ts`.

---

### ARCH-4 — LOW: OpenAPI auth scheme not declared
**File:** `backend/main.py`

The `HTTPBearer` dependency is not declared as a global security scheme. The Swagger UI "Authorize" button will not work at `/docs`.

**Action:** Pass the bearer scheme to the `FastAPI()` constructor or to individual route decorators.

---

## 7. Infrastructure / Docker

### INF-1 — MEDIUM: Container runs as root
**File:** `Dockerfile`

No `USER` directive is set. The application runs as root inside the container.

**Action:**
```dockerfile
RUN adduser --disabled-password --gecos '' appuser
USER appuser
```

---

### INF-2 — MEDIUM: `uv pip install --system` bypasses isolation
**File:** `Dockerfile:17`

`--system` installs into the system Python rather than a virtual environment, which can conflict with base image packages.

**Action:** Use `uv venv /app/.venv && uv pip install -r pyproject.toml`, or switch to `uv sync` with a lockfile.

---

### INF-3 — MEDIUM: No lockfile — builds are not reproducible
**File:** `Dockerfile:17`; `backend/pyproject.toml`

Dependencies use `>=` version constraints. Two builds on different dates may install different package versions.

**Action:** Commit a `uv.lock` file and use `uv sync --frozen` in the Dockerfile.

---

### INF-4 — LOW: No `restart` policy in `docker-compose.yml`
**File:** `docker-compose.yml`

If the container crashes, it will not restart automatically.

**Action:** Add `restart: unless-stopped` to the `kanban` service.

---

### INF-5 — INFO: No `HEALTHCHECK` in Dockerfile
**File:** `Dockerfile`

`GET /api/health` exists but is not wired up as a Docker health check.

**Action:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8000/api/health || exit 1
```

---

## Summary Table

| ID | Severity | Area | Location | Summary |
|---|---|---|---|---|
| SEC-1 | Critical | Security | `auth.py:5,9–10` | Hardcoded JWT secret and credentials |
| SEC-2 | High | Security | `models.py` | No input length validation |
| SEC-3 | High | Security | `main.py:227–229` | Silent swallow of AI validation errors |
| SEC-4 | High | Security | `database.py:20` | SHA-256 password hashing without salt |
| SEC-5 | Medium | Security | `main.py` | No CORS configuration |
| SEC-6 | Medium | Security | `page.tsx:15`; `api.ts:10` | JWT in localStorage |
| SEC-7 | Medium | Security | `main.py` | No rate limiting on login or AI chat |
| SEC-8 | Low | Security | repo root | No `.env.example` |
| BUG-1 | High | Correctness | `KanbanColumn.tsx:48` | API call on every rename keystroke |
| BUG-2 | High | Correctness | `KanbanBoard.tsx:288` | Possible `undefined` card at render |
| BUG-3 | High | Correctness | `database.py:27–32` | New DB connection per sub-operation |
| BUG-4 | Medium | Correctness | `main.py:98–101,197–200` | Duplicate identical endpoints |
| BUG-5 | Medium | Correctness | `database.py:155–177` | Implicit rollback on partial write |
| BUG-6 | Medium | Correctness | `kanban.ts:18–72` | Fixture IDs mismatch backend columns |
| BUG-7 | Medium | Correctness | `conftest.py:22–31` | File-delete isolation fragile on Windows |
| BUG-8 | Low | Correctness | `kanban.ts:164–168` | `createId` is dead code |
| BUG-9 | Low | Correctness | `main.py:125` | Imports inside function bodies |
| BUG-10 | Low | Correctness | `conftest.py:12` | `KANBAN_TEST_DB` env var never read |
| TST-2 | High | Testing | `KanbanBoard.test.tsx` | No tests for optimistic rollback on failure |
| TST-3 | Medium | Testing | `KanbanBoard.test.tsx` | No unit test for drag-end integration |
| TST-4 | Medium | Testing | `test_api.py` | No test for partial write failure |
| TST-5 | Medium | Testing | `kanban.test.ts` | `moveCard` edge cases untested |
| TST-6 | Medium | Testing | `playwright.config.ts` | Only Chromium; no Firefox/WebKit |
| TST-7 | Info | Testing | `pyproject.toml:24` | `asyncio_mode` key targets wrong library |
| QUA-1 | Medium | Quality | `main.py:111–191` | Ownership-check pattern repeated 4× |
| QUA-2 | Medium | Quality | `ChatSidebar.tsx:12–19` | Module-level mutable state for ID counter |
| QUA-3 | Medium | Quality | `KanbanCard.tsx:31–38` | Edit always commits both fields |
| QUA-4 | Low | Quality | `main.py:35–37` | `LoginRequest` defined in wrong file |
| QUA-5 | Low | Quality | `main.py:9` | Unused `ai_chat` alias |
| QUA-6 | Low | Quality | `KanbanBoard.tsx:88–97` | Drag handlers not memoized |
| QUA-7 | Low | Quality | `KanbanCard.tsx:40–43` | Enter commits textarea; Shift+Enter not handled |
| PERF-1 | High | Performance | `database.py:124–152` | N+1 queries in `load_board` |
| PERF-2 | Medium | Performance | `database.py:38–63` | No indexes on FK columns |
| PERF-3 | Medium | Performance | `ai.py:72` | Full board JSON with `indent=2` per AI call |
| PERF-4 | Low | Performance | `KanbanBoard.tsx:75` | `useMemo` on object ref always re-runs |
| ARCH-1 | Medium | Architecture | `database.py:155–177` | Full-replace save; last-write-wins |
| ARCH-2 | Medium | Architecture | `page.tsx:46–48` | Board refresh via full remount |
| ARCH-3 | Low | Architecture | `kanban.ts:18–72` | Fixture data in production bundle |
| ARCH-4 | Low | Architecture | `main.py` | OpenAPI auth scheme not declared |
| INF-1 | Medium | Infrastructure | `Dockerfile` | Container runs as root |
| INF-2 | Medium | Infrastructure | `Dockerfile:17` | `uv pip --system` bypasses isolation |
| INF-3 | Medium | Infrastructure | `Dockerfile`; `pyproject.toml` | No lockfile, non-reproducible builds |
| INF-4 | Low | Infrastructure | `docker-compose.yml` | No restart policy |
| INF-5 | Info | Infrastructure | `Dockerfile` | No `HEALTHCHECK` instruction |

---

## Priority Fix Order

For a pre-production hardening pass, address in this order:

1. **SEC-1** — hardcoded credentials and JWT secret; blocks any internet exposure
2. **BUG-1** — rename API storm; visible, reproducible, trivially fixed with debounce or blur-commit
3. **BUG-2** — `undefined` card crash; add a one-line filter guard
4. **PERF-1** — N+1 in `load_board`; single JOIN query rewrite, high impact for low effort
5. **SEC-2** — add `Field(max_length=...)` to all Pydantic string fields
6. **INF-1** — two lines in Dockerfile to drop root execution
7. **QUA-1** — extract ownership-check helper; reduces ~80 lines of duplication to ~20
8. **BUG-4** — delete one of the two duplicate board-save endpoints
