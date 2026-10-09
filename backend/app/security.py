from contextvars import ContextVar
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

authenticated_user_id: ContextVar[int | None] = ContextVar("authenticated_user_id", default=None)
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    return password_hash.verify(password, stored_hash)


def create_access_token(user_id: int) -> str:
    if len(settings.auth_secret_key.encode("utf-8")) < 32:
        raise RuntimeError("Authentication is not configured.")
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=settings.auth_token_expire_minutes),
        },
        settings.auth_secret_key,
        algorithm="HS256",
    )


def get_token_user_id(token: str) -> int | None:
    if len(settings.auth_secret_key.encode("utf-8")) < 32:
        return None
    try:
        payload = jwt.decode(token, settings.auth_secret_key, algorithms=["HS256"])
        subject = payload.get("sub")
        return int(subject) if isinstance(subject, str) and subject.isdecimal() else None
    except (jwt.InvalidTokenError, TypeError, ValueError):
        return None
