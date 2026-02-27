# Database Schema

SQLite database created automatically on first run. File: `kanban.db` in the backend working directory.

## Tables

### users

| Column        | Type    | Constraints          |
|---------------|---------|----------------------|
| id            | INTEGER | PRIMARY KEY          |
| username      | TEXT    | UNIQUE NOT NULL      |
| password_hash | TEXT    | NOT NULL             |

Seeded on first run with a single user (`user` / hashed `password`).

### boards

| Column     | Type    | Constraints              |
|------------|---------|--------------------------|
| id         | INTEGER | PRIMARY KEY              |
| user_id    | INTEGER | FK -> users.id, NOT NULL |
| name       | TEXT    | NOT NULL                 |
| created_at | TEXT    | ISO 8601, NOT NULL       |

One board per user for MVP. Created automatically on first `GET /api/board`.

### columns

| Column   | Type    | Constraints               |
|----------|---------|---------------------------|
| id       | TEXT    | PRIMARY KEY (e.g. "col-backlog") |
| board_id | INTEGER | FK -> boards.id, NOT NULL |
| title    | TEXT    | NOT NULL                  |
| position | INTEGER | NOT NULL                  |

Position determines left-to-right ordering. Five default columns created with each new board.

### cards

| Column    | Type    | Constraints                |
|-----------|---------|----------------------------|
| id        | TEXT    | PRIMARY KEY (e.g. "card-abc") |
| column_id | TEXT    | FK -> columns.id, NOT NULL |
| title     | TEXT    | NOT NULL                   |
| details   | TEXT    | NOT NULL DEFAULT 'No details yet.' |
| position  | INTEGER | NOT NULL                   |

Position determines top-to-bottom ordering within a column. No direct `board_id` -- derived through the column.

## Notes

- All foreign keys use `ON DELETE CASCADE` so deleting a board removes its columns and cards.
- IDs for columns and cards are text strings matching the frontend format (`col-*`, `card-*`).
- `password_hash` uses a simple hash even for the hardcoded MVP credentials, keeping the schema ready for real auth later.
- `position` integers are sequential starting from 0. Reordering reassigns positions.
