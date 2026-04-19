from __future__ import annotations

import os

from app.backend.api.core.security import create_access_token, verify_password
from app_shared.database import User, get_db
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session
from fastapi import Depends
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


@router.post(
    "/login",
    summary="Login user",
    response_model=LoginResponse,
)
async def login(body: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    _require_env("JWT_SECRET")

    email = str(body.email).strip().lower()
    password = body.password or ""

    if not email or "@" not in email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email")

    backend_mode = os.getenv("BACKEND_MODE", "").strip().lower()
    demo_email = os.getenv("DEMO_EMAIL", "").strip().lower()
    demo_password = os.getenv("DEMO_PASSWORD", "")
    if backend_mode != "api" and demo_email and demo_password:
        if email != demo_email or password != demo_password:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        token = create_access_token({"sub": email})
        return LoginResponse(access_token=token, email=email)

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token({"sub": email})
    return LoginResponse(access_token=token, email=email)
