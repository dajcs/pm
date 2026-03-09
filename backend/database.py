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
        """)

        # Migrations: add new columns if they don't exist
        for migration_sql in [
            "ALTER TABLE cards ADD COLUMN due_date TEXT",
            "ALTER TABLE cards ADD COLUMN priority TEXT NOT NULL DEFAULT 'none'",
            "ALTER TABLE boards ADD COLUMN description TEXT NOT NULL DEFAULT ''",
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

        for col_id, title, position in DEFAULT_COLUMNS:
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
        cols = await db.execute_fetchall(
            "SELECT id, title FROM columns WHERE board_id = ? ORDER BY position",
            (board_id,),
        )
        card_rows = await db.execute_fetchall(
            """SELECT cards.id, cards.column_id, cards.title, cards.details, cards.due_date, cards.priority
               FROM cards
               JOIN columns ON cards.column_id = columns.id
               WHERE columns.board_id = ?
               ORDER BY columns.position, cards.position""",
            (board_id,),
        )
        cards_by_col: dict[str, list[str]] = {col["id"]: [] for col in cols}
        cards: dict = {}
        for card in card_rows:
            card_id = card["id"]
            col_id = card["column_id"]
            cards[card_id] = {
                "id": card_id,
                "title": card["title"],
                "details": card["details"],
                "due_date": card["due_date"],
                "priority": card["priority"] or "none",
            }
            if col_id in cards_by_col:
                cards_by_col[col_id].append(card_id)
        columns = [
            {"id": col["id"], "title": col["title"], "cardIds": cards_by_col[col["id"]]}
            for col in cols
        ]
        return {"columns": columns, "cards": cards}
    finally:
        await db.close()


async def save_board(board_id: int, data: dict) -> None:
    """Replace the entire board content (columns + cards) with the provided data."""
    db = await get_db()
    try:
        await db.execute("DELETE FROM columns WHERE board_id = ?", (board_id,))
        for position, col in enumerate(data["columns"]):
            await db.execute(
                "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
                (col["id"], board_id, col["title"], position),
            )
            for card_pos, card_id in enumerate(col.get("cardIds", [])):
                card = data["cards"].get(card_id)
                if card:
                    await db.execute(
                        "INSERT INTO cards (id, column_id, title, details, position, due_date, priority) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            card["id"], col["id"], card["title"],
                            card.get("details", "No details yet."),
                            card_pos,
                            card.get("due_date"),
                            card.get("priority", "none"),
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
        card_id = f"card-{uuid.uuid4().hex[:8]}"
        await db.execute(
            "INSERT INTO cards (id, column_id, title, details, position, due_date, priority) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (card_id, column_id, title, details, position, due_date, priority),
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
        field_map = {
            "title": "title",
            "details": "details",
            "due_date": "due_date",
            "priority": "priority",
        }
        fields, values = [], []
        for key, col in field_map.items():
            if key in updates:
                fields.append(f"{col} = ?")
                values.append(updates[key])
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
    """Return stats: total cards, cards per column, overdue count."""
    from datetime import date
    db = await get_db()
    try:
        cols = await db.execute_fetchall(
            "SELECT id, title FROM columns WHERE board_id = ? ORDER BY position",
            (board_id,),
        )
        today = date.today().isoformat()
        cards_by_column = {}
        total = 0
        overdue = 0
        for col in cols:
            rows = await db.execute_fetchall(
                "SELECT id, due_date FROM cards WHERE column_id = ?", (col["id"],)
            )
            count = len(rows)
            cards_by_column[col["title"]] = count
            total += count
            for row in rows:
                if row["due_date"] and row["due_date"] < today:
                    overdue += 1
        return {
            "total_cards": total,
            "cards_by_column": cards_by_column,
            "overdue_count": overdue,
        }
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
