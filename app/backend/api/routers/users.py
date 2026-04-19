from __future__ import annotations

from app.backend.api.core.security import create_access_token, get_password_hash
from app.backend.api.routers.auth import LoginResponse
from app.backend.api.schemas.user import UserRegisterRequest
from app_shared.database import User, get_db
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=LoginResponse,
    summary="Create user account",
)
def register_user(body: UserRegisterRequest, db: Session = Depends(get_db)) -> LoginResponse:
    email = str(body.email).strip().lower()
    name = body.name.strip()

    if not email or "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email",
        )

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        name=name,
        email=email,
        hashed_password="",
    )
    try:
        user.hashed_password = get_password_hash(body.password)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password hashing backend error",
        ) from exc

    db.add(user)
    db.commit()

    try:
        token = create_access_token({"sub": email})
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return LoginResponse(access_token=token, email=email)
