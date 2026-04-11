"""
Database test endpoints for development and verification.

These endpoints verify that the database connection is working correctly.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app_shared.database import Market, User, get_db
from app_shared.schemas import MarketCreateSchema, MarketSchema

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
        market_count = db.query(Market).count()
        return {
            "status": "ok",
            "message": "Database connection successful",
            "user_count": user_count,
            "market_count": market_count,
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


@router.get("/markets", response_model=list[MarketSchema], summary="List all markets")
def list_markets(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """
    List all markets from the database.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        list: List of markets
    """
    try:
        markets = db.query(Market).offset(skip).limit(limit).all()
        return markets
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post(
    "/markets",
    response_model=MarketSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a market",
)
def create_market(market: MarketCreateSchema, db: Session = Depends(get_db)):
    """
    Create a new market in the database.

    Args:
        market: Market data

    Returns:
        Market: Created market with ID and timestamps
    """
    try:
        db_market = Market(**market.model_dump())
        db.add(db_market)
        db.commit()
        db.refresh(db_market)
        return db_market
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}
