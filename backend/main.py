from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ai import chat as ai_chat
from auth import VALID_PASSWORD, VALID_USERNAME, create_token, verify_token
from database import (
    create_card,
    delete_card,
    get_or_create_board,
    get_user_by_username,
    init_db,
    load_board,
    rename_column,
    save_board,
    update_card,
)
from models import (
    BoardData,
    CreateCardRequest,
    RenameColumnRequest,
    UpdateCardRequest,
)

STATIC_DIR = Path(__file__).parent / "static"

security = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str
    password: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Kanban Studio API", lifespan=lifespan)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    username = verify_token(credentials.credentials)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return username


async def get_board_id(username: str = Depends(get_current_user)) -> int:
    user = await get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return await get_or_create_board(user["id"])


# --- Health ---


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# --- Auth ---


@app.post("/api/auth/login")
async def login(body: LoginRequest):
    if body.username != VALID_USERNAME or body.password != VALID_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": create_token(body.username)}


@app.get("/api/auth/me")
async def me(username: str = Depends(get_current_user)):
    return {"username": username}


# --- Board ---


@app.get("/api/board")
async def get_board(board_id: int = Depends(get_board_id)):
    return await load_board(board_id)


@app.put("/api/board")
async def put_board(data: BoardData, board_id: int = Depends(get_board_id)):
    await save_board(board_id, data.model_dump())
    return await load_board(board_id)


# --- Cards ---


@app.post("/api/board/cards", status_code=201)
async def post_card(
    body: CreateCardRequest, board_id: int = Depends(get_board_id)
):
    from database import get_db

    # Verify the column belongs to this board
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id FROM columns WHERE id = ? AND board_id = ?",
            (body.column_id, board_id),
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Column not found")
    finally:
        await db.close()

    import uuid

    card_id = f"card-{uuid.uuid4().hex[:8]}"
    await create_card(body.column_id, card_id, body.title, body.details)
    return {"id": card_id, "title": body.title, "details": body.details}


@app.delete("/api/board/cards/{card_id}")
async def delete_card_endpoint(card_id: str, board_id: int = Depends(get_board_id)):
    # Verify card belongs to this board
    from database import get_db

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT cards.id FROM cards JOIN columns ON cards.column_id = columns.id WHERE cards.id = ? AND columns.board_id = ?",
            (card_id, board_id),
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Card not found")
    finally:
        await db.close()

    await delete_card(card_id)
    return {"ok": True}


@app.patch("/api/board/cards/{card_id}")
async def patch_card(
    card_id: str, body: UpdateCardRequest, board_id: int = Depends(get_board_id)
):
    from database import get_db

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT cards.id FROM cards JOIN columns ON cards.column_id = columns.id WHERE cards.id = ? AND columns.board_id = ?",
            (card_id, board_id),
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Card not found")
    finally:
        await db.close()

    await update_card(card_id, body.title, body.details)
    return {"ok": True}


# --- Columns ---


@app.patch("/api/board/columns/{column_id}")
async def patch_column(
    column_id: str, body: RenameColumnRequest, board_id: int = Depends(get_board_id)
):
    from database import get_db

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id FROM columns WHERE id = ? AND board_id = ?",
            (column_id, board_id),
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Column not found")
    finally:
        await db.close()

    await rename_column(column_id, body.title)
    return {"ok": True}


@app.put("/api/board/columns/order")
async def put_columns_order(data: BoardData, board_id: int = Depends(get_board_id)):
    await save_board(board_id, data.model_dump())
    return await load_board(board_id)


# --- AI ---


@app.post("/api/ai/test")
async def ai_test(_: str = Depends(get_current_user)):
    reply = await ai_chat([{"role": "user", "content": "What is 2+2?"}])
    return {"reply": reply}


# --- Static files (must be last) ---

if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
