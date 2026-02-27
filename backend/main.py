from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from auth import VALID_PASSWORD, VALID_USERNAME, create_token, verify_token

app = FastAPI(title="Kanban Studio API")

STATIC_DIR = Path(__file__).parent / "static"

security = HTTPBearer()


class LoginRequest(BaseModel):
    username: str
    password: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    username = verify_token(credentials.credentials)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return username


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/auth/login")
async def login(body: LoginRequest):
    if body.username != VALID_USERNAME or body.password != VALID_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": create_token(body.username)}


@app.get("/api/auth/me")
async def me(username: str = Depends(get_current_user)):
    return {"username": username}


# Serve static frontend -- must be last so /api routes take priority
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
