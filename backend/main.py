import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from ai import chat as ai_chat, chat_with_board
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
    ChatRequest,
    CreateCardRequest,
    RenameColumnRequest,
    UpdateCardRequest,
)

logger = logging.getLogger(__name__)

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


# --- AI ---


@app.post("/api/ai/test")
async def ai_test(_: str = Depends(get_current_user)):
    reply = await ai_chat([{"role": "user", "content": "What is 2+2?"}])
    return {"reply": reply}


@app.post("/api/ai/chat")
async def ai_chat_endpoint(body: ChatRequest, board_id: int = Depends(get_board_id)):
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
