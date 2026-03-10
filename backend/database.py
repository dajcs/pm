import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
import bcrypt

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "kanban.db"

DEFAULT_COLUMNS = [
    ("col-backlog", "Backlog", 0),
    ("col-todo", "To Do", 1),
    ("col-discovery", "Discovery", 2),
    ("col-progress", "In Progress", 3),
    ("col-done", "Done", 4),
]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def get_db_path() -> str:
    return str(DB_PATH)


async def get_db() -> aiosqlite.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(get_db_path())
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    return db


async def init_db() -> None:
    db = await get_db()
    try:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS boards (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS columns (
                id TEXT PRIMARY KEY,
                board_id INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                position INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cards (
                id TEXT PRIMARY KEY,
                column_id TEXT NOT NULL REFERENCES columns(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT 'No details yet.',
                position INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_boards_user_id ON boards(user_id);
            CREATE INDEX IF NOT EXISTS idx_columns_board_id ON columns(board_id);
            CREATE INDEX IF NOT EXISTS idx_cards_column_id ON cards(column_id);
            CREATE TABLE IF NOT EXISTS checklist_items (
                id INTEGER PRIMARY KEY,
                card_id TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
                text TEXT NOT NULL,
                checked INTEGER NOT NULL DEFAULT 0,
                position INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_checklist_card_id ON checklist_items(card_id);
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY,
                card_id TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
                username TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_comments_card_id ON comments(card_id);
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY,
                board_id INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
                username TEXT NOT NULL,
                action TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_activity_board_id ON activity_log(board_id);
        """)

        # Migrations: add new columns if they don't exist
        for migration_sql in [
            "ALTER TABLE cards ADD COLUMN due_date TEXT",
            "ALTER TABLE cards ADD COLUMN priority TEXT NOT NULL DEFAULT 'none'",
            "ALTER TABLE boards ADD COLUMN description TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE cards ADD COLUMN labels TEXT NOT NULL DEFAULT '[]'",
            "ALTER TABLE columns ADD COLUMN wip_limit INTEGER",
            "ALTER TABLE cards ADD COLUMN archived INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE cards ADD COLUMN assigned_to TEXT",
        ]:
            try:
                await db.execute(migration_sql)
                await db.commit()
            except Exception:
                pass  # Column already exists

        # Seed default user if not exists
        row = await db.execute_fetchall(
            "SELECT id FROM users WHERE username = ?", ("user",)
        )
        if not row:
            await db.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                ("user", hash_password("password")),
            )
        await db.commit()
    finally:
        await db.close()


async def get_user_by_username(username: str) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return {"id": row["id"], "username": row["username"], "password_hash": row["password_hash"]}
    finally:
        await db.close()


async def get_or_create_board(user_id: int) -> int:
    """Return the board id for the user, creating a default board if none exists."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id FROM boards WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return row["id"]

        now = datetime.now(timezone.utc).isoformat()
        cursor = await db.execute(
            "INSERT INTO boards (user_id, name, created_at) VALUES (?, ?, ?)",
            (user_id, "My Board", now),
        )
        board_id = cursor.lastrowid

        for _, title, position in DEFAULT_COLUMNS:
            col_id = f"col-{uuid.uuid4().hex[:8]}"
            await db.execute(
                "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
                (col_id, board_id, title, position),
            )

        await db.commit()
        return board_id
    finally:
        await db.close()


async def load_board(board_id: int) -> dict:
    """Load full board data as {columns: [...], cards: {...}} in two queries."""
    db = await get_db()
    try:
        import json as _json
        cols = await db.execute_fetchall(
            "SELECT id, title, wip_limit FROM columns WHERE board_id = ? ORDER BY position",
            (board_id,),
        )
        card_rows = await db.execute_fetchall(
            """SELECT cards.id, cards.column_id, cards.title, cards.details,
                      cards.due_date, cards.priority, cards.labels, cards.assigned_to
               FROM cards
               JOIN columns ON cards.column_id = columns.id
               WHERE columns.board_id = ? AND cards.archived = 0
               ORDER BY columns.position, cards.position""",
            (board_id,),
        )
        # Load comment counts for all cards on this board in one query
        comment_count_rows = await db.execute_fetchall(
            """SELECT cm.card_id, COUNT(*) as cnt
               FROM comments cm
               JOIN cards c ON cm.card_id = c.id
               JOIN columns col ON c.column_id = col.id
               WHERE col.board_id = ?
               GROUP BY cm.card_id""",
            (board_id,),
        )
        comment_counts: dict[str, int] = {r["card_id"]: r["cnt"] for r in comment_count_rows}
        # Load checklist summaries for all cards on this board in one query
        checklist_rows = await db.execute_fetchall(
            """SELECT ci.card_id,
                      COUNT(*) as total,
                      SUM(ci.checked) as done
               FROM checklist_items ci
               JOIN cards c ON ci.card_id = c.id
               JOIN columns col ON c.column_id = col.id
               WHERE col.board_id = ?
               GROUP BY ci.card_id""",
            (board_id,),
        )
        checklist_summary: dict[str, dict] = {
            r["card_id"]: {"total": r["total"], "done": int(r["done"] or 0)}
            for r in checklist_rows
        }
        cards_by_col: dict[str, list[str]] = {col["id"]: [] for col in cols}
        cards: dict = {}
        for card in card_rows:
            card_id = card["id"]
            col_id = card["column_id"]
            summary = checklist_summary.get(card_id, {"total": 0, "done": 0})
            cards[card_id] = {
                "id": card_id,
                "title": card["title"],
                "details": card["details"],
                "due_date": card["due_date"],
                "priority": card["priority"] or "none",
                "labels": _json.loads(card["labels"] or "[]"),
                "checklist_total": summary["total"],
                "checklist_done": summary["done"],
                "comment_count": comment_counts.get(card_id, 0),
                "assigned_to": card["assigned_to"],
            }
            if col_id in cards_by_col:
                cards_by_col[col_id].append(card_id)
        columns = [
            {
                "id": col["id"],
                "title": col["title"],
                "cardIds": cards_by_col[col["id"]],
                "wip_limit": col["wip_limit"],
            }
            for col in cols
        ]
        return {"columns": columns, "cards": cards}
    finally:
        await db.close()


async def save_board(board_id: int, data: dict) -> None:
    """Replace the entire board content (columns + cards) with the provided data."""
    db = await get_db()
    try:
        import json as _json
        await db.execute("DELETE FROM columns WHERE board_id = ?", (board_id,))
        for position, col in enumerate(data["columns"]):
            await db.execute(
                "INSERT INTO columns (id, board_id, title, position, wip_limit) VALUES (?, ?, ?, ?, ?)",
                (col["id"], board_id, col["title"], position, col.get("wip_limit")),
            )
            for card_pos, card_id in enumerate(col.get("cardIds", [])):
                card = data["cards"].get(card_id)
                if card:
                    await db.execute(
                        "INSERT INTO cards (id, column_id, title, details, position, due_date, priority, labels, assigned_to) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            card["id"], col["id"], card["title"],
                            card.get("details", "No details yet."),
                            card_pos,
                            card.get("due_date"),
                            card.get("priority", "none"),
                            _json.dumps(card.get("labels", [])),
                            card.get("assigned_to"),
                        ),
                    )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()


async def create_card(board_id: int, column_id: str, title: str, details: str, due_date: str | None = None, priority: str = "none") -> str | None:
    """Verify column belongs to board, insert card, return card_id. Returns None if column not found."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id FROM columns WHERE id = ? AND board_id = ?",
            (column_id, board_id),
        )
        if not await cursor.fetchone():
            return None
        cursor = await db.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 as next_pos FROM cards WHERE column_id = ?",
            (column_id,),
        )
        row = await cursor.fetchone()
        position = row["next_pos"]
        import json as _json
        card_id = f"card-{uuid.uuid4().hex[:8]}"
        await db.execute(
            "INSERT INTO cards (id, column_id, title, details, position, due_date, priority, labels) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (card_id, column_id, title, details, position, due_date, priority, "[]"),
        )
        await db.commit()
        return card_id
    finally:
        await db.close()


async def delete_card(card_id: str, board_id: int) -> bool:
    """Delete card if it belongs to the board. Returns True if deleted, False if not found."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """DELETE FROM cards WHERE id = ?
               AND column_id IN (SELECT id FROM columns WHERE board_id = ?)""",
            (card_id, board_id),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def archive_card(card_id: str, board_id: int) -> bool:
    """Soft-delete a card. Returns True if archived, False if not found."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """UPDATE cards SET archived = 1
               WHERE id = ? AND column_id IN (SELECT id FROM columns WHERE board_id = ?)
               AND archived = 0""",
            (card_id, board_id),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def restore_card(card_id: str, board_id: int) -> bool:
    """Restore an archived card. Returns True if restored, False if not found."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """UPDATE cards SET archived = 0
               WHERE id = ? AND column_id IN (SELECT id FROM columns WHERE board_id = ?)
               AND archived = 1""",
            (card_id, board_id),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def list_archived_cards(board_id: int) -> list[dict]:
    """Return all archived cards for a board."""
    db = await get_db()
    try:
        import json as _json
        rows = await db.execute_fetchall(
            """SELECT cards.id, cards.title, cards.details, cards.due_date,
                      cards.priority, cards.labels, columns.title as column_title
               FROM cards
               JOIN columns ON cards.column_id = columns.id
               WHERE columns.board_id = ? AND cards.archived = 1
               ORDER BY columns.position, cards.position""",
            (board_id,),
        )
        return [{
            "id": r["id"],
            "title": r["title"],
            "details": r["details"],
            "due_date": r["due_date"],
            "priority": r["priority"] or "none",
            "labels": _json.loads(r["labels"] or "[]"),
            "column_title": r["column_title"],
        } for r in rows]
    finally:
        await db.close()


async def update_card(card_id: str, board_id: int, updates: dict) -> bool:
    """Update card fields if it belongs to the board. Returns True if found, False if not found."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT cards.id FROM cards
               JOIN columns ON cards.column_id = columns.id
               WHERE cards.id = ? AND columns.board_id = ?""",
            (card_id, board_id),
        )
        if not await cursor.fetchone():
            return False
        import json as _json
        import json as _json
        field_map = {
            "title": "title",
            "details": "details",
            "due_date": "due_date",
            "priority": "priority",
            "assigned_to": "assigned_to",
        }
        fields, values = [], []
        for key, col in field_map.items():
            if key in updates:
                fields.append(f"{col} = ?")
                values.append(updates[key])
        if "labels" in updates:
            fields.append("labels = ?")
            values.append(_json.dumps(updates["labels"] or []))
        if not fields:
            return True  # card found, nothing to update
        values.append(card_id)
        await db.execute(f"UPDATE cards SET {', '.join(fields)} WHERE id = ?", values)
        await db.commit()
        return True
    finally:
        await db.close()


async def rename_column(column_id: str, board_id: int, title: str) -> bool:
    """Rename column if it belongs to the board. Returns True if updated, False if not found."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "UPDATE columns SET title = ? WHERE id = ? AND board_id = ?",
            (title, column_id, board_id),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def list_boards(user_id: int) -> list[dict]:
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT id, name, created_at, description FROM boards WHERE user_id = ? ORDER BY created_at",
            (user_id,),
        )
        return [{"id": r["id"], "name": r["name"], "created_at": r["created_at"], "description": r["description"] or ""} for r in rows]
    finally:
        await db.close()


async def create_board(user_id: int, name: str) -> int:
    """Create a new board with default columns. Returns board_id."""
    db = await get_db()
    try:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await db.execute(
            "INSERT INTO boards (user_id, name, created_at) VALUES (?, ?, ?)",
            (user_id, name, now),
        )
        board_id = cursor.lastrowid
        for _, title, position in DEFAULT_COLUMNS:
            col_id = f"col-{uuid.uuid4().hex[:8]}"
            await db.execute(
                "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
                (col_id, board_id, title, position),
            )
        await db.commit()
        return board_id
    finally:
        await db.close()


async def get_board_by_id(board_id: int, user_id: int) -> int | None:
    """Return board_id if it exists and belongs to user_id, else None."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id FROM boards WHERE id = ? AND user_id = ?",
            (board_id, user_id),
        )
        row = await cursor.fetchone()
        return row["id"] if row else None
    finally:
        await db.close()


async def rename_board(board_id: int, user_id: int, name: str) -> bool:
    db = await get_db()
    try:
        cursor = await db.execute(
            "UPDATE boards SET name = ? WHERE id = ? AND user_id = ?",
            (name, board_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def delete_board(board_id: int, user_id: int) -> str:
    """Delete board if owned by user and user has >1 board.
    Returns 'ok', 'not_found', or 'last_board'."""
    db = await get_db()
    try:
        count_rows = await db.execute_fetchall(
            "SELECT COUNT(*) as cnt FROM boards WHERE user_id = ?", (user_id,)
        )
        if count_rows[0]["cnt"] <= 1:
            owned = await db.execute(
                "SELECT id FROM boards WHERE id = ? AND user_id = ?", (board_id, user_id)
            )
            if not await owned.fetchone():
                return "not_found"
            return "last_board"
        cursor = await db.execute(
            "DELETE FROM boards WHERE id = ? AND user_id = ?",
            (board_id, user_id),
        )
        await db.commit()
        if cursor.rowcount == 0:
            return "not_found"
        return "ok"
    finally:
        await db.close()


async def create_user(username: str, password: str) -> int | None:
    """Create a new user. Returns user_id or None if username taken."""
    db = await get_db()
    try:
        try:
            cursor = await db.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, hash_password(password)),
            )
            await db.commit()
            return cursor.lastrowid
        except Exception:
            return None
    finally:
        await db.close()


async def add_column(board_id: int, title: str) -> str:
    """Add a new column to the board. Returns the new column_id."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 as next_pos FROM columns WHERE board_id = ?",
            (board_id,),
        )
        row = await cursor.fetchone()
        position = row["next_pos"]
        col_id = f"col-{uuid.uuid4().hex[:8]}"
        await db.execute(
            "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
            (col_id, board_id, title, position),
        )
        await db.commit()
        return col_id
    finally:
        await db.close()


async def delete_column(column_id: str, board_id: int) -> bool:
    """Delete column if it belongs to board. Returns True if deleted."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "DELETE FROM columns WHERE id = ? AND board_id = ?",
            (column_id, board_id),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def get_board_stats(board_id: int) -> dict:
    """Return comprehensive board stats including priority, assignment, and due-date breakdown."""
    from datetime import date, timedelta
    db = await get_db()
    try:
        cols = await db.execute_fetchall(
            "SELECT id, title FROM columns WHERE board_id = ? ORDER BY position",
            (board_id,),
        )
        today = date.today().isoformat()
        due_soon_cutoff = (date.today() + timedelta(days=3)).isoformat()
        cards_by_column: dict[str, int] = {}
        cards_by_priority: dict[str, int] = {}
        total = 0
        overdue = 0
        due_soon = 0
        assigned = 0

        for col in cols:
            rows = await db.execute_fetchall(
                "SELECT id, due_date, priority, assigned_to FROM cards WHERE column_id = ? AND archived = 0",
                (col["id"],),
            )
            count = len(rows)
            cards_by_column[col["title"]] = count
            total += count
            for row in rows:
                p = row["priority"] or "none"
                cards_by_priority[p] = cards_by_priority.get(p, 0) + 1
                if row["due_date"]:
                    if row["due_date"] < today:
                        overdue += 1
                    elif row["due_date"] <= due_soon_cutoff:
                        due_soon += 1
                if row["assigned_to"]:
                    assigned += 1

        return {
            "total_cards": total,
            "cards_by_column": cards_by_column,
            "overdue_count": overdue,
            "cards_by_priority": cards_by_priority,
            "due_soon_count": due_soon,
            "assigned_count": assigned,
            "unassigned_count": total - assigned,
        }
    finally:
        await db.close()


async def archive_column_cards(column_id: str, board_id: int) -> int:
    """Archive all non-archived cards in a column. Returns count archived."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """UPDATE cards SET archived = 1
               WHERE column_id = ? AND archived = 0
               AND column_id IN (SELECT id FROM columns WHERE board_id = ?)""",
            (column_id, board_id),
        )
        await db.commit()
        return cursor.rowcount
    finally:
        await db.close()


async def update_board_description(board_id: int, user_id: int, description: str) -> bool:
    db = await get_db()
    try:
        cursor = await db.execute(
            "UPDATE boards SET description = ? WHERE id = ? AND user_id = ?",
            (description, board_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def set_column_wip_limit(column_id: str, board_id: int, wip_limit: int | None) -> bool:
    """Set (or clear) WIP limit for a column. Returns True if updated."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "UPDATE columns SET wip_limit = ? WHERE id = ? AND board_id = ?",
            (wip_limit, column_id, board_id),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def _card_belongs_to_board(db: aiosqlite.Connection, card_id: str, board_id: int) -> bool:
    cursor = await db.execute(
        """SELECT 1 FROM cards JOIN columns ON cards.column_id = columns.id
           WHERE cards.id = ? AND columns.board_id = ?""",
        (card_id, board_id),
    )
    return await cursor.fetchone() is not None


async def get_checklist(card_id: str, board_id: int) -> list[dict] | None:
    """Return checklist items for a card, or None if card not found on board."""
    db = await get_db()
    try:
        if not await _card_belongs_to_board(db, card_id, board_id):
            return None
        rows = await db.execute_fetchall(
            "SELECT id, text, checked FROM checklist_items WHERE card_id = ? ORDER BY position",
            (card_id,),
        )
        return [{"id": r["id"], "text": r["text"], "checked": bool(r["checked"])} for r in rows]
    finally:
        await db.close()


async def add_checklist_item(card_id: str, board_id: int, text: str) -> int | None:
    """Add item to card's checklist. Returns item id or None if card not found."""
    db = await get_db()
    try:
        if not await _card_belongs_to_board(db, card_id, board_id):
            return None
        cursor = await db.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 as next_pos FROM checklist_items WHERE card_id = ?",
            (card_id,),
        )
        row = await cursor.fetchone()
        cursor = await db.execute(
            "INSERT INTO checklist_items (card_id, text, checked, position) VALUES (?, ?, 0, ?)",
            (card_id, text, row["next_pos"]),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def update_checklist_item(
    item_id: int, card_id: str, board_id: int,
    text: str | None, checked: bool | None
) -> bool:
    """Update text/checked on a checklist item. Returns True if updated."""
    db = await get_db()
    try:
        if not await _card_belongs_to_board(db, card_id, board_id):
            return False
        fields, values = [], []
        if text is not None:
            fields.append("text = ?")
            values.append(text)
        if checked is not None:
            fields.append("checked = ?")
            values.append(1 if checked else 0)
        if not fields:
            return True
        values.extend([item_id, card_id])
        cursor = await db.execute(
            f"UPDATE checklist_items SET {', '.join(fields)} WHERE id = ? AND card_id = ?",
            values,
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def delete_checklist_item(item_id: int, card_id: str, board_id: int) -> bool:
    """Delete a checklist item. Returns True if deleted."""
    db = await get_db()
    try:
        if not await _card_belongs_to_board(db, card_id, board_id):
            return False
        cursor = await db.execute(
            "DELETE FROM checklist_items WHERE id = ? AND card_id = ?",
            (item_id, card_id),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def get_comments(card_id: str, board_id: int) -> list[dict] | None:
    """Return comments for a card, or None if card not on board."""
    db = await get_db()
    try:
        if not await _card_belongs_to_board(db, card_id, board_id):
            return None
        rows = await db.execute_fetchall(
            "SELECT id, username, text, created_at FROM comments WHERE card_id = ? ORDER BY created_at",
            (card_id,),
        )
        return [{"id": r["id"], "username": r["username"], "text": r["text"], "created_at": r["created_at"]} for r in rows]
    finally:
        await db.close()


async def add_comment(card_id: str, board_id: int, username: str, text: str) -> int | None:
    """Add a comment to a card. Returns comment id or None if card not on board."""
    db = await get_db()
    try:
        if not await _card_belongs_to_board(db, card_id, board_id):
            return None
        now = datetime.now(timezone.utc).isoformat()
        cursor = await db.execute(
            "INSERT INTO comments (card_id, username, text, created_at) VALUES (?, ?, ?, ?)",
            (card_id, username, text, now),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def delete_comment(comment_id: int, card_id: str, board_id: int, username: str) -> str:
    """Delete a comment. Returns 'ok', 'not_found', or 'forbidden'."""
    db = await get_db()
    try:
        if not await _card_belongs_to_board(db, card_id, board_id):
            return "not_found"
        cursor = await db.execute(
            "SELECT id, username FROM comments WHERE id = ? AND card_id = ?",
            (comment_id, card_id),
        )
        row = await cursor.fetchone()
        if row is None:
            return "not_found"
        if row["username"] != username:
            return "forbidden"
        await db.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        await db.commit()
        return "ok"
    finally:
        await db.close()


async def add_activity(board_id: int, username: str, action: str) -> None:
    """Append an activity log entry for the board."""
    db = await get_db()
    try:
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO activity_log (board_id, username, action, created_at) VALUES (?, ?, ?, ?)",
            (board_id, username, action, now),
        )
        await db.commit()
    finally:
        await db.close()


async def get_activity(board_id: int, limit: int = 50) -> list[dict]:
    """Return recent activity for a board (most recent first)."""
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT id, username, action, created_at FROM activity_log WHERE board_id = ? ORDER BY created_at DESC LIMIT ?",
            (board_id, limit),
        )
        return [{"id": r["id"], "username": r["username"], "action": r["action"], "created_at": r["created_at"]} for r in rows]
    finally:
        await db.close()


async def search_cards(board_id: int, query: str) -> list[dict]:
    """Full-text search across card title, details, and comments. Returns matching card ids."""
    db = await get_db()
    try:
        q = f"%{query.lower()}%"
        rows = await db.execute_fetchall(
            """SELECT DISTINCT cards.id
               FROM cards
               JOIN columns ON cards.column_id = columns.id
               WHERE columns.board_id = ? AND cards.archived = 0
               AND (
                   LOWER(cards.title) LIKE ? OR
                   LOWER(cards.details) LIKE ? OR
                   EXISTS (
                       SELECT 1 FROM comments
                       WHERE comments.card_id = cards.id
                       AND LOWER(comments.text) LIKE ?
                   )
               )""",
            (board_id, q, q, q),
        )
        return [r["id"] for r in rows]
    finally:
        await db.close()


async def list_board_members(board_id: int) -> list[str]:
    """Return usernames of all users who have ever commented or been assigned on this board."""
    db = await get_db()
    try:
        # Board owner
        owner_rows = await db.execute_fetchall(
            "SELECT u.username FROM users u JOIN boards b ON b.user_id = u.id WHERE b.id = ?",
            (board_id,),
        )
        owner = {r["username"] for r in owner_rows}
        # Commenters
        commenter_rows = await db.execute_fetchall(
            """SELECT DISTINCT cm.username FROM comments cm
               JOIN cards c ON cm.card_id = c.id
               JOIN columns col ON c.column_id = col.id
               WHERE col.board_id = ?""",
            (board_id,),
        )
        commenters = {r["username"] for r in commenter_rows}
        # Activity actors
        actor_rows = await db.execute_fetchall(
            "SELECT DISTINCT username FROM activity_log WHERE board_id = ?",
            (board_id,),
        )
        actors = {r["username"] for r in actor_rows}
        return sorted(owner | commenters | actors)
    finally:
        await db.close()


async def export_board(board_id: int) -> dict:
    """Return full board data including archived cards, columns, and metadata."""
    db = await get_db()
    try:
        import json as _json
        board_row = await db.execute_fetchall(
            "SELECT id, name, description, created_at FROM boards WHERE id = ?", (board_id,)
        )
        if not board_row:
            return {}
        b = board_row[0]
        cols = await db.execute_fetchall(
            "SELECT id, title, wip_limit FROM columns WHERE board_id = ? ORDER BY position", (board_id,)
        )
        card_rows = await db.execute_fetchall(
            """SELECT cards.id, cards.column_id, cards.title, cards.details,
                      cards.due_date, cards.priority, cards.labels, cards.archived
               FROM cards JOIN columns ON cards.column_id = columns.id
               WHERE columns.board_id = ? ORDER BY columns.position, cards.position""",
            (board_id,),
        )
        cards = []
        for card in card_rows:
            cards.append({
                "id": card["id"],
                "column_id": card["column_id"],
                "title": card["title"],
                "details": card["details"],
                "due_date": card["due_date"],
                "priority": card["priority"] or "none",
                "labels": _json.loads(card["labels"] or "[]"),
                "archived": bool(card["archived"]),
            })
        return {
            "board": {"id": b["id"], "name": b["name"], "description": b["description"] or "", "created_at": b["created_at"]},
            "columns": [{"id": c["id"], "title": c["title"], "wip_limit": c["wip_limit"]} for c in cols],
            "cards": cards,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        await db.close()


async def update_user_password(user_id: int, new_password: str) -> None:
    db = await get_db()
    try:
        await db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(new_password), user_id),
        )
        await db.commit()
    finally:
        await db.close()
