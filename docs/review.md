# Code Review: Kanban Studio PM App

**Date:** 2026-03-09
**Reviewer:** Claude Code (claude-sonnet-4-6)
**Overall Score:** 82/100 — well-executed MVP with good architecture and test coverage; main concerns are security for production and a few edge-case bugs.

---

## Summary Table

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| Security | 1 | 2 | 2 | 1 | 6 |
| Architecture | — | — | 3 | 1 | 4 |
| Code Quality | — | — | 2 | 3 | 5 |
| Bugs | — | — | 3 | 2 | 5 |
| Performance | — | — | 1 | 1 | 2 |
| Tests | — | — | — | 4 | 4 |
| Deployment | — | — | 1 | 3 | 4 |
| Documentation | — | — | 1 | 1 | 2 |

---

## Security

### SEC-1 — JWT in localStorage [CRITICAL]
**Files:** `frontend/src/app/page.tsx:43`, `frontend/src/lib/api.ts:10`

JWT is stored in `localStorage`. Any XSS in the app or its dependencies can steal the token. Noted in deferred items (SEC-6); must be resolved before any public deployment.

**Fix:** httpOnly cookie with `SameSite=Strict`.

---

### SEC-2 — Hardcoded default credentials [HIGH]
**File:** `backend/auth.py:10-11`

```python
VALID_USERNAME = os.environ.get("APP_USERNAME", "user")
VALID_PASSWORD = os.environ.get("APP_PASSWORD", "password")
```

If env vars are not set, the app starts with `user`/`password`. There is no startup check that enforces non-default values.

**Fix:** Raise `RuntimeError` at startup if values match defaults (or are unset).

---

### SEC-3 — AI board_update silently dropped on validation failure [HIGH]
**File:** `backend/main.py:199-206`

When the AI returns an invalid `board_update`, the error is logged at `WARNING` and the mutation is silently discarded. The client receives HTTP 200 with `board_update: null` and has no way to distinguish "AI chose not to update" from "update was invalid."

**Fix:** Return HTTP 400 with a detail string, or at minimum elevate the log to `ERROR`.

---

### SEC-4 — Overly permissive CORS [MEDIUM]
**File:** `backend/main.py:62-78`

```python
allow_methods=["*"],
allow_headers=["*"],
```

**Fix:**
```python
allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
allow_headers=["Content-Type", "Authorization"],
```

---

### SEC-5 — No HTTPS enforcement or security headers [LOW]
No security headers middleware (X-Frame-Options, CSP, HSTS). Acceptable for a single-container MVP behind a reverse proxy, but should be documented.

---

## Architecture

### ARCH-1 — Single-user schema is misleading [MEDIUM]
**File:** `backend/database.py:44-67`

The schema has a `users` table and `user_id` foreign keys, implying multi-user support, but the app only supports one account per container. This is confusing for future maintainers.

**Fix:** Add a comment at the top of `database.py` explaining the constraint, or drop `user_id` from the schema.

---

### ARCH-2 — Full delete-replace in save_board [MEDIUM]
**File:** `backend/database.py:165-187`

`save_board()` deletes all columns/cards and re-inserts from the client payload on every save. Acknowledged in deferred items. The immediate risk is that a bug in the client can silently wipe all data.

**Fix (near-term):** Add a pre-delete snapshot log. **Fix (long-term):** Atomic merge (insert/update/delete only what changed).

---

### ARCH-3 — No granular column-reorder endpoint [LOW]
Reordering columns calls `PUT /api/board` (full board replace). A dedicated `PUT /api/board/columns/order` endpoint would be more efficient and reduce blast radius.

---

## Code Quality

### CODE-1 — asyncio_mode missing from pyproject.toml [MEDIUM]
**File:** `backend/pyproject.toml`

`CLAUDE.md` documents `asyncio_mode = "auto"` but it is absent from the file. Tests pass currently because `conftest.py` sets the env var, but this is fragile across pytest/anyio version changes.

**Fix:**
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

---

### CODE-2 — New DB connection per request [MEDIUM]
**File:** `backend/database.py` — all async functions

Every endpoint opens and closes its own `aiosqlite` connection. Under any load this causes unnecessary connection churn. For a single-user MVP it is acceptable but should be addressed before multi-user deployment.

**Fix:** Share a connection or pool at startup; inject via FastAPI dependency.

---

### CODE-3 — Inconsistent error handling in AI endpoint [LOW]
AI validation failures are `WARNING`-logged and silently swallowed (see SEC-3 above). All other endpoints raise `HTTPException` on data errors. Inconsistent across the codebase.

---

### CODE-4 — Inline return type on createCard [LOW]
**File:** `frontend/src/lib/api.ts:55`

Return type is an inline anonymous object instead of a named type. Minor consistency issue with the rest of the file.

---

## Bugs

### BUG-1 — Race condition in optimistic card delete [MEDIUM]
**File:** `frontend/src/components/KanbanBoard.tsx:186-206`

`prev` is captured at call time. If two cards are deleted in quick succession and the first fails, reverting to `prev` restores the board to a state before the second delete succeeded — the second card reappears.

**Fix:** Capture `prevBoard` explicitly before `setBoard`:
```typescript
const handleDeleteCard = (columnId: string, cardId: string) => {
  const prevBoard = board;
  setBoard({ ... });
  api.deleteCard(cardId).catch(() => setBoard(prevBoard));
};
```

---

### BUG-2 — Drag within a column does not persist [MEDIUM]
**File:** `backend/database.py:145`, `175-181`

`cards.position` is written on save but cards are queried with `ORDER BY cards.position`. However, intra-column drag-and-drop only updates client state; it does not call any API. On page reload, cards return to creation order.

**Fix:** Call the board save API after any intra-column drag, or add a dedicated `PATCH /api/board/columns/{id}/cards/order` endpoint.

---

### BUG-3 — Missing card silently dropped from column [LOW]
**File:** `frontend/src/components/KanbanBoard.tsx:318`

```typescript
column.cardIds.map((id) => board.cards[id]).filter((c): c is Card => c !== undefined)
```

If a card ID exists in a column but not in `board.cards`, it is silently omitted from rendering. The user sees fewer cards than expected with no indication of the problem.

**Fix:** Log a console warning for each missing card ID.

---

### BUG-4 — No timeout on OpenRouter API calls [LOW]
**File:** `backend/ai.py:53-59`

No timeout is set on the OpenRouter HTTP call. A slow/hung upstream will hold the request open for the Uvicorn worker timeout (typically 60 s).

**Fix:**
```python
response = await asyncio.wait_for(
    client.chat.completions.create(...),
    timeout=30.0
)
```

---

### BUG-5 — New card form has no Escape key handler [LOW]
**File:** `frontend/src/components/NewCardForm.tsx`

The Cancel button closes the form, but pressing Escape does nothing. Standard UX expectation.

**Fix:** Add `onKeyDown` handler for `Escape` on the form element.

---

## Performance

### PERF-1 — Full board replace on every drag-and-drop [MEDIUM]
**File:** `frontend/src/components/KanbanBoard.tsx:136`, `backend/database.py:165`

Moving a card triggers `PUT /api/board`, which deletes and re-inserts every column and card. For a board with 100 cards this is 100+ SQL statements per operation.

**Fix:** Add `PATCH /api/board/columns/{id}/cards` to update only the affected column(s).

---

### PERF-2 — O(n) column lookup per drag event [LOW]
**File:** `frontend/src/lib/kanban.ts:18-25`

`isColumnId` uses `Array.some()`, called multiple times per drag event. Negligible for typical board sizes but trivial to fix.

**Fix:** Build a `Set` or `Map` once and reuse it.

---

## Tests

### TEST-1 — AI edge cases not covered [LOW]
No tests for truncated JSON, oversized responses, or invalid Unicode from the AI service.

### TEST-2 — No concurrent operation tests [LOW]
No tests for simultaneous drag operations or race conditions in the optimistic update pattern.

### TEST-3 — No E2E test for AI board mutation [LOW]
No Playwright test verifying the full flow: user sends message → AI creates/moves card → board updates visibly.

### TEST-4 — No database constraint violation tests [LOW]
No tests for FK cascades, unique constraint violations, or orphaned cards.

---

## Deployment

### DEPLOY-1 — No HEALTHCHECK in Dockerfile [LOW]
Docker Compose cannot auto-restart an unresponsive container without it. Noted in deferred items (INF-5).

**Fix:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1
```

---

### DEPLOY-2 — uv.lock missing [MEDIUM]
**File:** `Dockerfile`

Dockerfile installs from `pyproject.toml` but no `uv.lock` exists, so builds are not reproducible. Noted in deferred items (INF-3).

**Fix:** Run `uv lock` in `backend/` and commit the resulting file.

---

### DEPLOY-3 — No .dockerignore [LOW]
Docker build context includes `node_modules`, `.git`, `__pycache__`, test files, and virtual envs.

**Fix:** Add `.dockerignore` excluding those paths.

---

## Documentation

### DOCS-1 — No security guidance in README [MEDIUM]
No documentation covering: JWT storage limitation, requirement to change default credentials, recommended reverse-proxy setup.

### DOCS-2 — No API docs endpoint [LOW]
FastAPI's auto-generated docs are disabled. Consider enabling `/api/docs` at minimum for development.

---

## Prioritized Recommendations

### Before any production deployment
1. **SEC-1** — Replace localStorage JWT with httpOnly cookie
2. **SEC-2** — Fail startup if credentials are still default
3. **BUG-2** — Fix intra-column card order not persisting on reload
4. **CODE-1** — Add `asyncio_mode = "auto"` to `pyproject.toml`

### Short-term (next sprint)
5. **BUG-1** — Fix race condition in optimistic delete revert
6. **SEC-3 / CODE-3** — Return 400 on AI board_update validation failure
7. **DEPLOY-2** — Generate and commit `uv.lock`
8. **DOCS-1** — Add security guidance to README

### Medium-term (before scaling)
9. **CODE-2** — Implement DB connection pooling
10. **PERF-1** — Add incremental board update endpoint
11. **ARCH-2** — Log pre-delete snapshot before save_board wipe
12. **TEST-2** — Add concurrency tests

### Nice-to-have (post-MVP)
- HEALTHCHECK in Dockerfile
- `.dockerignore`
- Security headers middleware
- OpenAPI docs endpoint
- Multi-user support

---

## Strengths

- Clean component architecture with clear separation (KanbanBoard / Column / Card / ChatSidebar)
- Comprehensive test coverage (32 backend + 30 frontend unit + 6 E2E)
- Correct optimistic UI pattern with revert on API failure
- Type safety enforced end-to-end (TypeScript + Pydantic)
- Async-first backend (FastAPI + aiosqlite)
- Correct non-root Docker user with `gosu` privilege drop
- Smart dnd-kit collision detection (hybrid pointer/closestCenter)
- User-visible error messages with auto-dismiss
