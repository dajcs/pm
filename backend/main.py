import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from ai import chat_with_board
from auth import VALID_PASSWORD, VALID_USERNAME, create_token, verify_token
from database import (
    add_column,
    create_board,
    create_card,
    create_user,
    delete_board,
    delete_card,
    delete_column,
    get_board_by_id,
    get_or_create_board,
    get_user_by_username,
    init_db,
    list_boards,
    load_board,
    rename_board,
    rename_column,
    save_board,
    update_card,
    update_user_password,
    verify_password,
)
from models import (
    BoardData,
    ChangePasswordRequest,
    ChatRequest,
    CreateBoardRequest,
    CreateCardRequest,
    CreateColumnRequest,
    LoginRequest,
    RegisterRequest,
    RenameBoardRequest,
    RenameColumnRequest,
    UpdateCardRequest,
)

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"

_RATE_LIMIT_ENABLED = os.environ.get("DISABLE_RATE_LIMIT", "").lower() != "true"

limiter = Limiter(key_func=get_remote_address)

security = HTTPBearer(auto_error=False)


def _limit(rate: str):
    """Apply rate limit unless disabled (for tests)."""
    if _RATE_LIMIT_ENABLED:
        return limiter.limit(rate)
    return lambda f: f


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

app = FastAPI(title="Kanban Studio API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    username = verify_token(credentials.credentials)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return username


async def get_board_id(
    board_id: int | None = Query(default=None),
    username: str = Depends(get_current_user),
) -> int:
    user = await get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if board_id is not None:
        verified = await get_board_by_id(board_id, user["id"])
        if verified is None:
            raise HTTPException(status_code=404, detail="Board not found")
        return board_id
    return await get_or_create_board(user["id"])


# --- Health ---


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# --- Auth ---


@app.post("/api/auth/login")
@_limit("5/minute")
async def login(request: Request, body: LoginRequest):
    user = await get_user_by_username(body.username)
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": create_token(body.username)}


@app.get("/api/auth/me")
async def me(username: str = Depends(get_current_user)):
    return {"username": username}


# --- Registration ---


@app.post("/api/auth/register", status_code=201)
async def register(body: RegisterRequest):
    user_id = await create_user(body.username, body.password)
    if user_id is None:
        raise HTTPException(status_code=409, detail="Username already taken")
    return {"token": create_token(body.username)}


@app.post("/api/auth/change-password")
async def change_password_endpoint(
    body: ChangePasswordRequest, username: str = Depends(get_current_user)
):
    user = await get_user_by_username(username)
    if user is None or not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid current password")
    await update_user_password(user["id"], body.new_password)
    return {"ok": True}


# --- Boards (multi-board management) ---


@app.get("/api/boards")
async def list_boards_endpoint(username: str = Depends(get_current_user)):
    user = await get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return await list_boards(user["id"])


@app.post("/api/boards", status_code=201)
async def create_board_endpoint(
    body: CreateBoardRequest, username: str = Depends(get_current_user)
):
    user = await get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    board_id = await create_board(user["id"], body.name)
    return {"id": board_id, "name": body.name}


@app.patch("/api/boards/{bid}")
async def rename_board_endpoint(
    bid: int, body: RenameBoardRequest, username: str = Depends(get_current_user)
):
    user = await get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if not await rename_board(bid, user["id"], body.name):
        raise HTTPException(status_code=404, detail="Board not found")
    return {"ok": True}


@app.delete("/api/boards/{bid}")
async def delete_board_endpoint(bid: int, username: str = Depends(get_current_user)):
    user = await get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    result = await delete_board(bid, user["id"])
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Board not found")
    if result == "last_board":
        raise HTTPException(status_code=400, detail="Cannot delete your only board")
    return {"ok": True}


# --- Board ---


@app.get("/api/board")
async def get_board(board_id: int = Depends(get_board_id)):
    return await load_board(board_id)


@app.put("/api/board")
async def put_board(data: BoardData, board_id: int = Depends(get_board_id)):
    try:
        await save_board(board_id, data.model_dump())
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail=f"Board data error: {exc}")
    return await load_board(board_id)


# --- Cards ---


@app.post("/api/board/cards", status_code=201)
async def post_card(body: CreateCardRequest, board_id: int = Depends(get_board_id)):
    card_id = await create_card(board_id, body.column_id, body.title, body.details)
    if card_id is None:
        raise HTTPException(status_code=404, detail="Column not found")
    return {"id": card_id, "title": body.title, "details": body.details}


@app.delete("/api/board/cards/{card_id}")
async def delete_card_endpoint(card_id: str, board_id: int = Depends(get_board_id)):
    if not await delete_card(card_id, board_id):
        raise HTTPException(status_code=404, detail="Card not found")
    return {"ok": True}


@app.patch("/api/board/cards/{card_id}")
async def patch_card(
    card_id: str, body: UpdateCardRequest, board_id: int = Depends(get_board_id)
):
    if not await update_card(card_id, board_id, body.title, body.details):
        raise HTTPException(status_code=404, detail="Card not found")
    return {"ok": True}


# --- Columns ---


@app.patch("/api/board/columns/{column_id}")
async def patch_column(
    column_id: str, body: RenameColumnRequest, board_id: int = Depends(get_board_id)
):
    if not await rename_column(column_id, board_id, body.title):
        raise HTTPException(status_code=404, detail="Column not found")
    return {"ok": True}


@app.post("/api/board/columns", status_code=201)
async def add_column_endpoint(
    body: CreateColumnRequest, board_id: int = Depends(get_board_id)
):
    col_id = await add_column(board_id, body.title)
    return {"id": col_id, "title": body.title}


@app.delete("/api/board/columns/{column_id}")
async def delete_column_endpoint(
    column_id: str, board_id: int = Depends(get_board_id)
):
    if not await delete_column(column_id, board_id):
        raise HTTPException(status_code=404, detail="Column not found")
    return {"ok": True}


# --- AI ---


@app.post("/api/ai/test")
async def ai_test(_: str = Depends(get_current_user)):
    from ai import chat as _ai_chat
    reply = await _ai_chat([{"role": "user", "content": "What is 2+2?"}])
    return {"reply": reply}


@app.post("/api/ai/chat")
@_limit("30/minute")
async def ai_chat_endpoint(request: Request, body: ChatRequest, board_id: int = Depends(get_board_id)):
    board_state = await load_board(board_id)
    result = await chat_with_board(
        user_message=body.message,
        history=[m.model_dump() for m in body.history],
        board_state=board_state,
    )
    if result["board_update"] is not None:
        try:
            updated = BoardData.model_validate(result["board_update"])
            await save_board(board_id, updated.model_dump())
            result["board_update"] = await load_board(board_id)
        except ValidationError as exc:
            logger.warning("AI board_update validation failed: %s", exc)
            result["board_update"] = None
    return result


# --- Static files (must be last) ---

if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
