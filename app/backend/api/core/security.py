from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against a hashed password."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hashes a plain-text password."""
    return pwd_context.hash(password)


def create_access_token(payload: dict[str, Any], expires_minutes: int = 60) -> str:
    secret = os.getenv("JWT_SECRET", "").strip()
    if not secret:
        raise ValueError("Missing required env var: JWT_SECRET")

    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_minutes)

    to_encode = {
        **payload,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(to_encode, secret, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate JWT access token payload."""

    secret = os.getenv("JWT_SECRET", "").strip()
    if not secret:
        raise ValueError("Missing required env var: JWT_SECRET")

    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc

    if not isinstance(payload, dict):
        raise ValueError("Invalid token payload")
    return payload
