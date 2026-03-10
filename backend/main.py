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
    add_activity,
    export_board,
    list_board_members,
    search_cards,
    add_checklist_item,
    add_column,
    add_comment,
    archive_card,
    archive_column_cards,
    duplicate_card,
    create_board,
    create_card,
    create_user,
    delete_board,
    delete_card,
    delete_checklist_item,
    delete_column,
    delete_comment,
    get_activity,
    get_board_by_id,
    get_board_members_with_roles,
    get_board_stats,
    get_checklist,
    get_comments,
    get_or_create_board,
    get_user_by_username,
    init_db,
    invite_board_member,
    is_board_owner,
    list_archived_cards,
    list_boards,
    list_shared_boards,
    load_board,
    rename_board,
    rename_column,
    restore_card,
    save_board,
    set_column_wip_limit,
    update_board_description,
    add_card_dependency,
    get_card_dependencies,
    get_dashboard,
    remove_board_member,
    remove_card_dependency,
    update_card,
    update_checklist_item,
    update_user_password,
    verify_password,
)
from models import (
    ActivityEntry,
    AddChecklistItemRequest,
    AddCommentRequest,
    ArchivedCard,
    BoardMember,
    LogActivityRequest,
    BoardData,
    BoardStatsResponse,
    ChangePasswordRequest,
    ChatRequest,
    Comment,
    AddDependencyRequest,
    CreateBoardFromTemplateRequest,
    CreateBoardRequest,
    CreateCardRequest,
    CreateColumnRequest,
    InviteMemberRequest,
    LoginRequest,
    RegisterRequest,
    RenameBoardRequest,
    RenameColumnRequest,
    SetWipLimitRequest,
    UpdateBoardDescriptionRequest,
    UpdateCardRequest,
    UpdateChecklistItemRequest,
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
    owned = await list_boards(user["id"])
    shared = await list_shared_boards(user["id"])
    # Mark shared boards so frontend can distinguish
    for b in shared:
        b["shared"] = True
    for b in owned:
        b.setdefault("shared", False)
    return owned + shared


@app.post("/api/boards", status_code=201)
async def create_board_endpoint(
    body: CreateBoardRequest, username: str = Depends(get_current_user)
):
    user = await get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    board_id = await create_board(user["id"], body.name)
    return {"id": board_id, "name": body.name}


BOARD_TEMPLATES: dict[str, list[str]] = {
    "sprint": ["Backlog", "In Progress", "Testing", "Done"],
    "marketing": ["Ideas", "Planning", "In Progress", "Review", "Published"],
    "personal": ["To Do", "Doing", "Done"],
    "product": ["Discovery", "Design", "Development", "QA", "Released"],
    "hiring": ["Applied", "Screening", "Interview", "Offer", "Hired"],
}


@app.post("/api/boards/from-template", status_code=201)
async def create_board_from_template_endpoint(
    body: CreateBoardFromTemplateRequest, username: str = Depends(get_current_user)
):
    user = await get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    template_cols = BOARD_TEMPLATES.get(body.template.lower())
    if template_cols is None:
        raise HTTPException(status_code=400, detail=f"Unknown template '{body.template}'. Available: {list(BOARD_TEMPLATES)}")
    board_id = await create_board(user["id"], body.name)
    # Add template columns (create_board already adds default columns, we need to use them or replace)
    # Get the newly created board and add template columns after loading
    for title in template_cols:
        await add_column(board_id, title)
    return {"id": board_id, "name": body.name, "template": body.template}


@app.get("/api/boards/templates")
async def list_templates_endpoint():
    return [{"name": k, "columns": v} for k, v in BOARD_TEMPLATES.items()]


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


@app.get("/api/boards/{bid}/stats")
async def board_stats(bid: int, username: str = Depends(get_current_user)):
    user = await get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    verified = await get_board_by_id(bid, user["id"])
    if verified is None:
        raise HTTPException(status_code=404, detail="Board not found")
    return await get_board_stats(bid)


@app.get("/api/boards/{bid}/activity")
async def board_activity(bid: int, username: str = Depends(get_current_user)):
    user = await get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    verified = await get_board_by_id(bid, user["id"])
    if verified is None:
        raise HTTPException(status_code=404, detail="Board not found")
    return await get_activity(bid)


@app.post("/api/boards/{bid}/activity")
async def log_board_activity(
    bid: int, body: LogActivityRequest, username: str = Depends(get_current_user)
):
    user = await get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    verified = await get_board_by_id(bid, user["id"])
    if verified is None:
        raise HTTPException(status_code=404, detail="Board not found")
    await add_activity(bid, username, body.action)
    return {"ok": True}


@app.get("/api/board/search")
async def search_cards_endpoint(
    q: str = Query(min_length=1, max_length=200),
    board_id: int = Depends(get_board_id),
):
    return await search_cards(board_id, q)


@app.get("/api/boards/{bid}/members")
async def board_members_endpoint(bid: int, username: str = Depends(get_current_user)):
    user = await get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    verified = await get_board_by_id(bid, user["id"])
    if verified is None:
        raise HTTPException(status_code=404, detail="Board not found")
    return await list_board_members(bid)


@app.get("/api/boards/{bid}/members/roles")
async def board_members_with_roles_endpoint(bid: int, username: str = Depends(get_current_user)):
    user = await get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    verified = await get_board_by_id(bid, user["id"])
    if verified is None:
        raise HTTPException(status_code=404, detail="Board not found")
    return await get_board_members_with_roles(bid)


@app.post("/api/boards/{bid}/invite")
async def invite_member_endpoint(
    bid: int, body: InviteMemberRequest, username: str = Depends(get_current_user)
):
    user = await get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    result = await invite_board_member(bid, user["id"], body.username)
    if result == "not_owner":
        raise HTTPException(status_code=403, detail="Only the board owner can invite members")
    if result == "user_not_found":
        raise HTTPException(status_code=404, detail=f"User '{body.username}' not found")
    if result == "already_member":
        raise HTTPException(status_code=409, detail="User is already a member")
    await add_activity(bid, username, f"invited {body.username} to the board")
    return {"ok": True}


@app.delete("/api/boards/{bid}/members/{member_username}")
async def remove_member_endpoint(
    bid: int, member_username: str, username: str = Depends(get_current_user)
):
    user = await get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    removed = await remove_board_member(bid, user["id"], member_username)
    if not removed:
        raise HTTPException(status_code=403, detail="Not authorized or member not found")
    await add_activity(bid, username, f"removed {member_username} from the board")
    return {"ok": True}


@app.get("/api/boards/{bid}/export")
async def export_board_endpoint(bid: int, username: str = Depends(get_current_user)):
    user = await get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    verified = await get_board_by_id(bid, user["id"])
    if verified is None:
        raise HTTPException(status_code=404, detail="Board not found")
    return await export_board(bid)


@app.patch("/api/boards/{bid}/description")
async def update_board_description_endpoint(
    bid: int, body: UpdateBoardDescriptionRequest, username: str = Depends(get_current_user)
):
    user = await get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if not await update_board_description(bid, user["id"], body.description):
        raise HTTPException(status_code=404, detail="Board not found")
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
async def post_card(
    body: CreateCardRequest,
    board_id: int = Depends(get_board_id),
    username: str = Depends(get_current_user),
):
    card_id = await create_card(board_id, body.column_id, body.title, body.details, body.due_date, body.priority)
    if card_id is None:
        raise HTTPException(status_code=404, detail="Column not found")
    await add_activity(board_id, username, f"created card \"{body.title}\"")
    return {"id": card_id, "title": body.title, "details": body.details, "due_date": body.due_date, "priority": body.priority}


@app.delete("/api/board/cards/{card_id}")
async def delete_card_endpoint(
    card_id: str,
    board_id: int = Depends(get_board_id),
    username: str = Depends(get_current_user),
):
    if not await delete_card(card_id, board_id):
        raise HTTPException(status_code=404, detail="Card not found")
    await add_activity(board_id, username, "permanently deleted a card")
    return {"ok": True}


@app.post("/api/board/cards/{card_id}/duplicate")
async def duplicate_card_endpoint(
    card_id: str,
    board_id: int = Depends(get_board_id),
    username: str = Depends(get_current_user),
):
    result = await duplicate_card(card_id, board_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Card not found")
    await add_activity(board_id, username, f"duplicated card \"{result['title']}\"")
    return result


@app.get("/api/board/cards/{card_id}/dependencies")
async def get_card_deps_endpoint(
    card_id: str, board_id: int = Depends(get_board_id)
):
    return await get_card_dependencies(card_id, board_id)


@app.post("/api/board/cards/{card_id}/dependencies")
async def add_card_dep_endpoint(
    card_id: str,
    body: AddDependencyRequest,
    board_id: int = Depends(get_board_id),
    username: str = Depends(get_current_user),
):
    result = await add_card_dependency(card_id, body.depends_on_id, board_id)
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Card not found")
    if result == "self":
        raise HTTPException(status_code=400, detail="Card cannot depend on itself")
    if result == "duplicate":
        raise HTTPException(status_code=409, detail="Dependency already exists")
    return {"ok": True}


@app.delete("/api/board/cards/{card_id}/dependencies/{depends_on_id}")
async def remove_card_dep_endpoint(
    card_id: str,
    depends_on_id: str,
    board_id: int = Depends(get_board_id),
):
    removed = await remove_card_dependency(card_id, depends_on_id, board_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Dependency not found")
    return {"ok": True}


@app.get("/api/dashboard")
async def dashboard_endpoint(username: str = Depends(get_current_user)):
    user = await get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return await get_dashboard(user["id"])


@app.post("/api/board/cards/{card_id}/archive")
async def archive_card_endpoint(
    card_id: str,
    board_id: int = Depends(get_board_id),
    username: str = Depends(get_current_user),
):
    if not await archive_card(card_id, board_id):
        raise HTTPException(status_code=404, detail="Card not found")
    await add_activity(board_id, username, "archived a card")
    return {"ok": True}


@app.post("/api/board/cards/{card_id}/restore")
async def restore_card_endpoint(
    card_id: str,
    board_id: int = Depends(get_board_id),
    username: str = Depends(get_current_user),
):
    if not await restore_card(card_id, board_id):
        raise HTTPException(status_code=404, detail="Archived card not found")
    await add_activity(board_id, username, "restored a card")
    return {"ok": True}


@app.get("/api/board/archived-cards")
async def list_archived_cards_endpoint(board_id: int = Depends(get_board_id)):
    return await list_archived_cards(board_id)


@app.post("/api/board/columns/{column_id}/archive-all")
async def archive_column_cards_endpoint(
    column_id: str,
    board_id: int = Depends(get_board_id),
    username: str = Depends(get_current_user),
):
    count = await archive_column_cards(column_id, board_id)
    if count > 0:
        await add_activity(board_id, username, f"archived {count} card(s) from a column")
    return {"archived_count": count}


@app.patch("/api/board/cards/{card_id}")
async def patch_card(
    card_id: str, body: UpdateCardRequest, board_id: int = Depends(get_board_id)
):
    updates = body.model_dump(exclude_unset=True)
    if "title" in updates and updates["title"] is None:
        updates.pop("title")
    if "details" in updates and updates["details"] is None:
        updates.pop("details")
    if not await update_card(card_id, board_id, updates):
        raise HTTPException(status_code=404, detail="Card not found")
    return {"ok": True}


# --- Checklists ---


@app.get("/api/board/cards/{card_id}/checklist")
async def get_checklist_endpoint(card_id: str, board_id: int = Depends(get_board_id)):
    items = await get_checklist(card_id, board_id)
    if items is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return items


@app.post("/api/board/cards/{card_id}/checklist", status_code=201)
async def add_checklist_item_endpoint(
    card_id: str, body: AddChecklistItemRequest, board_id: int = Depends(get_board_id)
):
    item_id = await add_checklist_item(card_id, board_id, body.text)
    if item_id is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return {"id": item_id, "text": body.text, "checked": False}


@app.patch("/api/board/cards/{card_id}/checklist/{item_id}")
async def update_checklist_item_endpoint(
    card_id: str, item_id: int, body: UpdateChecklistItemRequest,
    board_id: int = Depends(get_board_id)
):
    if not await update_checklist_item(item_id, card_id, board_id, body.text, body.checked):
        raise HTTPException(status_code=404, detail="Checklist item not found")
    return {"ok": True}


@app.delete("/api/board/cards/{card_id}/checklist/{item_id}")
async def delete_checklist_item_endpoint(
    card_id: str, item_id: int, board_id: int = Depends(get_board_id)
):
    if not await delete_checklist_item(item_id, card_id, board_id):
        raise HTTPException(status_code=404, detail="Checklist item not found")
    return {"ok": True}


# --- Comments ---


@app.get("/api/board/cards/{card_id}/comments")
async def get_comments_endpoint(card_id: str, board_id: int = Depends(get_board_id)):
    items = await get_comments(card_id, board_id)
    if items is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return items


@app.post("/api/board/cards/{card_id}/comments", status_code=201)
async def add_comment_endpoint(
    card_id: str,
    body: AddCommentRequest,
    board_id: int = Depends(get_board_id),
    username: str = Depends(get_current_user),
):
    comment_id = await add_comment(card_id, board_id, username, body.text)
    if comment_id is None:
        raise HTTPException(status_code=404, detail="Card not found")
    from datetime import datetime, timezone
    return {"id": comment_id, "username": username, "text": body.text, "created_at": datetime.now(timezone.utc).isoformat()}


@app.delete("/api/board/cards/{card_id}/comments/{comment_id}")
async def delete_comment_endpoint(
    card_id: str,
    comment_id: int,
    board_id: int = Depends(get_board_id),
    username: str = Depends(get_current_user),
):
    result = await delete_comment(comment_id, card_id, board_id, username)
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Comment not found")
    if result == "forbidden":
        raise HTTPException(status_code=403, detail="Cannot delete another user's comment")
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


@app.put("/api/board/columns/{column_id}/wip-limit")
async def set_wip_limit_endpoint(
    column_id: str, body: SetWipLimitRequest, board_id: int = Depends(get_board_id)
):
    if not await set_column_wip_limit(column_id, board_id, body.wip_limit):
        raise HTTPException(status_code=404, detail="Column not found")
    return {"ok": True}


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
