from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, status
from jose import jwt
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Missing required env var: {name}",
        )
    return value


def _create_access_token(payload: dict[str, Any], expires_minutes: int = 60) -> str:
    secret = _require_env("JWT_SECRET")
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_minutes)

    to_encode = {
        **payload,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(to_encode, secret, algorithm="HS256")


@router.post(
    "/login",
    summary="Login (demo user MVP)",
    response_model=LoginResponse,
)
async def login(body: LoginRequest) -> LoginResponse:
    demo_email = _require_env("DEMO_EMAIL").lower()
    demo_password = _require_env("DEMO_PASSWORD")

    email = str(body.email).strip().lower()
    password = body.password or ""

    if not email or "@" not in email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email")

    if email != demo_email or password != demo_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = _create_access_token({"sub": email})
    return LoginResponse(access_token=token, email=email)
