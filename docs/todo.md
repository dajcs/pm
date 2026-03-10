# TODO

Potential future improvements, in rough priority order.

## High priority

- **Notification delivery improvements** — polling every 30 s works but Server-Sent Events or WebSocket would give real-time push without client-side intervals
- **Sprint burndown chart** — day-by-day remaining card count for an active sprint; needs a `sprint_snapshots` table or computed from activity log
- **Board import** — parse and restore a previously exported JSON file; the export endpoint exists but there is no import UI or endpoint yet
- **Card move column tracking** — record which column a card moved from/to in the activity log so history is meaningful
- **Role-based permissions** — member role currently has full write access; add `viewer` (read-only) and enforce per-endpoint
- **httpOnly cookie auth** — JWT is stored in `localStorage` (SEC-6 in PLAN.md); move to httpOnly cookie for XSS resistance

## Medium priority

- **Custom card fields** — user-defined fields per board (text, number, select); needs `custom_fields` and `card_field_values` tables
- **Recurring cards** — cards that auto-recreate on a schedule (daily, weekly, sprint); needs a cron/scheduler
- **Keyboard shortcuts** — `/` focuses search already; add `n` for new card, `b` for board selector, `Esc` to close modals (partially done)
- **Time tracking report UI** — `GET /api/boards/{id}/time-report` exists but there is no frontend panel to view aggregated hours per-board; could add to StatsPanel
- **Mention autocomplete** — `@username` in comments currently just parses on submit; add a dropdown picker as the user types
- **Card attachments** — upload/download files attached to a card; needs object storage or base64-in-DB for small files
- **Board description editor** — the description field exists in the DB and API (`PATCH /api/boards/{id}/description`) but has no UI

## Low priority / nice-to-have

- **Dark mode** — CSS custom properties are already themed; adding a `dark` class toggle would be straightforward
- **Drag-to-sprint** — drag a card directly onto a sprint name to assign it
- **Sprint velocity** — track how many story points (or card counts) were completed per sprint over time
- **Email notifications** — send an email in addition to the in-app notification on assignment/mention; needs SMTP config
- **Two-factor authentication** — TOTP or email OTP; the auth layer is simple JWT right now
- **Audit log export** — download the activity log as CSV
- **Multi-language / i18n** — all strings are currently hardcoded in English
- **Playwright E2E coverage** — only 6 E2E tests; cover login, card CRUD, sprint creation, notifications

## Infrastructure / ops

- `uv lock` — `uv.lock` file is missing; run `uv lock` inside `backend/` on Windows or CI (INF-3)
- `HEALTHCHECK` in Dockerfile (INF-5)
- CI pipeline — no GitHub Actions workflow yet; add lint + test jobs for both frontend and backend on push
- Docker compose — single-container works but a `docker-compose.yml` would simplify local dev with volume mounts
