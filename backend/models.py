from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class Card(BaseModel):
    id: str
    title: str = Field(max_length=200)
    details: str = Field(default="No details yet.", max_length=4000)
    due_date: str | None = None
    priority: str = "none"
    labels: list[str] = []
    checklist_total: int = 0
    checklist_done: int = 0
    comment_count: int = 0
    assigned_to: str | None = None


class ChecklistItem(BaseModel):
    id: int
    text: str
    checked: bool


class AddChecklistItemRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class UpdateChecklistItemRequest(BaseModel):
    text: str | None = Field(default=None, max_length=500)
    checked: bool | None = None


class Column(BaseModel):
    id: str
    title: str = Field(max_length=200)
    cardIds: list[str] = []
    wip_limit: int | None = None


class BoardData(BaseModel):
    columns: list[Column]
    cards: dict[str, Card]


class CreateCardRequest(BaseModel):
    column_id: str
    title: str = Field(max_length=200)
    details: str = Field(default="No details yet.", max_length=4000)
    due_date: str | None = None
    priority: str = "none"


class UpdateCardRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    details: str | None = Field(default=None, max_length=4000)
    due_date: str | None = None
    priority: str | None = None
    labels: list[str] | None = None
    assigned_to: str | None = None


class SetWipLimitRequest(BaseModel):
    wip_limit: int | None = None  # None clears the limit


class BoardStatsResponse(BaseModel):
    total_cards: int
    cards_by_column: dict[str, int]
    overdue_count: int
    cards_by_priority: dict[str, int] = {}
    due_soon_count: int = 0
    assigned_count: int = 0
    unassigned_count: int = 0


class UpdateBoardDescriptionRequest(BaseModel):
    description: str = Field(max_length=2000)


class RenameColumnRequest(BaseModel):
    title: str = Field(max_length=200)


class ChatMessage(BaseModel):
    role: str
    content: str = Field(max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(max_length=2000)
    history: list[ChatMessage] = []


class CreateBoardRequest(BaseModel):
    name: str = Field(max_length=200)


class RenameBoardRequest(BaseModel):
    name: str = Field(max_length=200)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=100)


class CreateColumnRequest(BaseModel):
    title: str = Field(max_length=200)


class Comment(BaseModel):
    id: int
    username: str
    text: str
    created_at: str


class AddCommentRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class ActivityEntry(BaseModel):
    id: int
    username: str
    action: str
    created_at: str


class LogActivityRequest(BaseModel):
    action: str = Field(min_length=1, max_length=500)


class ArchivedCard(BaseModel):
    id: str
    title: str
    details: str
    due_date: str | None = None
    priority: str = "none"
    labels: list[str] = []
    column_title: str


class InviteMemberRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)


class BoardMember(BaseModel):
    username: str
    role: str
    joined_at: str | None = None


class CreateBoardFromTemplateRequest(BaseModel):
    name: str = Field(max_length=200)
    template: str = Field(max_length=50)


class AddDependencyRequest(BaseModel):
    depends_on_id: str = Field(min_length=1, max_length=50)


class TimeEntry(BaseModel):
    id: int
    username: str
    hours: float
    description: str
    date: str
    created_at: str


class AddTimeEntryRequest(BaseModel):
    hours: float = Field(gt=0, le=24)
    description: str = Field(default="", max_length=500)
    date: str = Field(min_length=1, max_length=10)


class BoardTimeReportEntry(BaseModel):
    card_id: str
    card_title: str
    username: str
    total_hours: float
