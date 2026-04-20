from __future__ import annotations

import os
from typing import Annotated

from app_shared.database import User, get_db
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

bearer_scheme = HTTPBearer(auto_error=False)


def _get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "").strip()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing required env var: JWT_SECRET",
        )
    return secret


def _extract_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    token: str | None = Query(default=None),
) -> str:
    if token:
        return token.strip()

    if credentials and credentials.scheme.lower() == "bearer":
        return credentials.credentials.strip()

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(_extract_token),
) -> User:
    secret = _get_jwt_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    email = str(payload.get("sub") or "").strip().lower()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user