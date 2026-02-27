from pydantic import BaseModel


class Card(BaseModel):
    id: str
    title: str
    details: str = "No details yet."


class Column(BaseModel):
    id: str
    title: str
    cardIds: list[str] = []


class BoardData(BaseModel):
    columns: list[Column]
    cards: dict[str, Card]


class CreateCardRequest(BaseModel):
    column_id: str
    title: str
    details: str = "No details yet."


class UpdateCardRequest(BaseModel):
    title: str | None = None
    details: str | None = None


class RenameColumnRequest(BaseModel):
    title: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
