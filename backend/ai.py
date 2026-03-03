"""OpenRouter AI wrapper using the openai client."""

import json
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI, APIError

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

MODEL = "openai/gpt-oss-120b:free"

_api_key = os.environ.get("OPENROUTER_API_KEY", "")

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=_api_key,
)

SYSTEM_PROMPT = """\
You are a project management assistant for a Kanban board app called Kanban Studio.
You can view and modify the user's Kanban board.

The board has columns, each with an id, title, and list of cardIds.
Cards have an id, title, and details field.

When the user asks you to create, move, edit, or delete cards, return the updated
board state in the "board_update" field. Otherwise set "board_update" to null.

IMPORTANT: You must ALWAYS respond with valid JSON matching this exact schema:
{
  "message": "<your text reply to the user>",
  "board_update": <the full updated board object, or null>
}

The board object schema (when not null):
{
  "columns": [{"id": "col-xxx", "title": "Column Name", "cardIds": ["card-xxx"]}],
  "cards": {"card-xxx": {"id": "card-xxx", "title": "Card Title", "details": "Card details"}}
}

Rules:
- Keep card IDs in the format "card-" followed by 8 hex characters (e.g. "card-a1b2c3d4")
- When creating new cards, generate new IDs in that format
- Always include ALL existing columns and cards in board_update, not just changed ones
- If you are not modifying the board, set board_update to null
- Do not wrap the JSON in markdown code fences

Current board state:
"""


async def chat(messages: list[dict], model: str = MODEL) -> str:
    """Send messages to OpenRouter and return the assistant's reply."""
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
    )
    return response.choices[0].message.content or ""


async def chat_with_board(
    user_message: str,
    history: list[dict],
    board_state: dict,
    model: str = MODEL,
) -> dict:
    """Send a chat message with board context; return parsed structured response.

    Returns dict with "message" (str) and "board_update" (dict | None).
    """
    system_content = SYSTEM_PROMPT + json.dumps(board_state, separators=(",", ":"))

    messages: list[dict] = [{"role": "system", "content": system_content}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    try:
        raw = await chat(messages, model=model)
    except APIError as e:
        return {"message": f"AI service error: {e.message}", "board_update": None}

    # Parse the structured JSON response
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # If JSON parsing fails, treat the whole response as a plain message
        return {"message": raw, "board_update": None}

    return {
        "message": parsed.get("message", raw),
        "board_update": parsed.get("board_update"),
    }

