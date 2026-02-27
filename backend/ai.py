"""OpenRouter AI wrapper using the openai client."""

import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

MODEL = "openai/gpt-oss-120b:free"

_api_key = os.environ.get("OPENROUTER_API_KEY", "")

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=_api_key,
)


async def chat(messages: list[dict], model: str = MODEL) -> str:
    """Send messages to OpenRouter and return the assistant's reply."""
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
    )
    return response.choices[0].message.content or ""
