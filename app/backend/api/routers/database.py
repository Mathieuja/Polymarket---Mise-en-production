"""
Database test endpoints for development and verification.

These endpoints verify that the database connection is working correctly.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.backend.database.database import get_db
from app.backend.database.models import User

router = APIRouter(prefix="/db", tags=["database"])


@router.get(
    "/test",
    status_code=status.HTTP_200_OK,
    summary="Test database connection",
)
def test_db_connection(db: Session = Depends(get_db)):
    """
    Test the database connection by attempting a simple query.

    Returns:
        dict: Status message and user count
    """
    try:
        # Simple query to verify database connection
        user_count = db.query(User).count()
        return {
            "status": "ok",
            "message": "Database connection successful",
            "user_count": user_count,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Database connection failed: {str(e)}",
        }


@router.post(
    "/test-create-user",
    status_code=status.HTTP_201_CREATED,
    summary="Create a test user",
)
def create_test_user(
    name: str = "Test User",
    email: str = "test@example.com",
    db: Session = Depends(get_db),
):
    """
    Create a test user in the database.

    Args:
        name: User's name
        email: User's email address

    Returns:
        dict: Created user information
    """
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            return {
                "status": "already_exists",
                "user": {
                    "id": existing_user.id,
                    "name": existing_user.name,
                    "email": existing_user.email,
                },
            }

        # Create new user
        user = User(name=name, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)

        return {
            "status": "created",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
            },
        }
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": f"Failed to create user: {str(e)}",
        }
