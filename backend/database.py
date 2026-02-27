import hashlib
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

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
    return hashlib.sha256(password.encode()).hexdigest()


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
        """)

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
    """Load full board data as {columns: [...], cards: {...}}."""
    db = await get_db()
    try:
        cols = await db.execute_fetchall(
            "SELECT id, title, position FROM columns WHERE board_id = ? ORDER BY position",
            (board_id,),
        )
        columns = []
        cards = {}
        for col in cols:
            col_id = col["id"]
            card_rows = await db.execute_fetchall(
                "SELECT id, title, details, position FROM cards WHERE column_id = ? ORDER BY position",
                (col_id,),
            )
            card_ids = []
            for card in card_rows:
                card_id = card["id"]
                card_ids.append(card_id)
                cards[card_id] = {
                    "id": card_id,
                    "title": card["title"],
                    "details": card["details"],
                }
            columns.append({"id": col_id, "title": col["title"], "cardIds": card_ids})
        return {"columns": columns, "cards": cards}
    finally:
        await db.close()


async def save_board(board_id: int, data: dict) -> None:
    """Replace the entire board content (columns + cards) with the provided data."""
    db = await get_db()
    try:
        # Delete existing columns (cards cascade)
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
                        "INSERT INTO cards (id, column_id, title, details, position) VALUES (?, ?, ?, ?, ?)",
                        (card["id"], col["id"], card["title"], card.get("details", "No details yet."), card_pos),
                    )

        await db.commit()
    finally:
        await db.close()


async def create_card(column_id: str, card_id: str, title: str, details: str) -> None:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 as next_pos FROM cards WHERE column_id = ?",
            (column_id,),
        )
        row = await cursor.fetchone()
        position = row["next_pos"]
        await db.execute(
            "INSERT INTO cards (id, column_id, title, details, position) VALUES (?, ?, ?, ?, ?)",
            (card_id, column_id, title, details, position),
        )
        await db.commit()
    finally:
        await db.close()


async def delete_card(card_id: str) -> bool:
    db = await get_db()
    try:
        cursor = await db.execute("DELETE FROM cards WHERE id = ?", (card_id,))
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def update_card(card_id: str, title: str | None, details: str | None) -> bool:
    db = await get_db()
    try:
        fields = []
        values = []
        if title is not None:
            fields.append("title = ?")
            values.append(title)
        if details is not None:
            fields.append("details = ?")
            values.append(details)
        if not fields:
            return False
        values.append(card_id)
        cursor = await db.execute(
            f"UPDATE cards SET {', '.join(fields)} WHERE id = ?", values
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def rename_column(column_id: str, title: str) -> bool:
    db = await get_db()
    try:
        cursor = await db.execute(
            "UPDATE columns SET title = ? WHERE id = ?", (title, column_id)
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()
