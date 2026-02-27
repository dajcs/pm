from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

SECRET_KEY = "kanban-studio-dev-secret-key"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

VALID_USERNAME = "user"
VALID_PASSWORD = "password"


def create_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> str | None:
    """Return the username if the token is valid, else None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
