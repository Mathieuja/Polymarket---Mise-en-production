from __future__ import annotations

import os
from datetime import datetime

from app_shared.database import User, get_db
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.backend.api.core.security import create_access_token, verify_password
from app.backend.api.dependencies.auth import get_current_active_user

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    expires_in: int = 3600


class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class UserInfoResponse(BaseModel):
    id: int
    email: str
    roles: list[str] = Field(default_factory=lambda: ["user"])
    status: str = "active"
    created_at: datetime


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8)
    new_password: str = Field(min_length=8)
    new_password_confirm: str


class ChangePasswordResponse(BaseModel):
    message: str
    user_id: int
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
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        token = create_access_token({"sub": email})
        return LoginResponse(access_token=token, email=email)

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token({"sub": email})
    return LoginResponse(access_token=token, email=email)


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    summary="Refresh access token",
)
async def refresh_token(
    current_user: User = Depends(get_current_active_user),
) -> TokenRefreshResponse:
    token = create_access_token({"sub": current_user.email})
    return TokenRefreshResponse(access_token=token)


@router.get(
    "/me",
    response_model=UserInfoResponse,
    summary="Get current user info",
)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
) -> UserInfoResponse:
    return UserInfoResponse(
        id=current_user.id,
        email=current_user.email,
        created_at=current_user.created_at,
    )


@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    summary="Change user password",
)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ChangePasswordResponse:
    if body.new_password != body.new_password_confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New passwords do not match")

    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    from app.backend.api.core.security import get_password_hash

    current_user.hashed_password = get_password_hash(body.new_password)
    db.add(current_user)
    db.commit()

    return ChangePasswordResponse(
        message="Password changed successfully",
        user_id=current_user.id,
        email=current_user.email,
    )
