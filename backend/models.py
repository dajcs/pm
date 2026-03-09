from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class Card(BaseModel):
    id: str
    title: str = Field(max_length=200)
    details: str = Field(default="No details yet.", max_length=4000)


class Column(BaseModel):
    id: str
    title: str = Field(max_length=200)
    cardIds: list[str] = []


class BoardData(BaseModel):
    columns: list[Column]
    cards: dict[str, Card]


class CreateCardRequest(BaseModel):
    column_id: str
    title: str = Field(max_length=200)
    details: str = Field(default="No details yet.", max_length=4000)


class UpdateCardRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    details: str | None = Field(default=None, max_length=4000)


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
