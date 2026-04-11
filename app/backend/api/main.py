"""
FastAPI application main file for the backend API.
"""

from contextlib import asynccontextmanager

from app_shared.database import init_db
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.backend.api.routers import database_router, health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan manager.

    At startup, initializes database connections, loads configuration, etc.
    At shutdown, handles all deconnections, cleanup, etc.
    """
    # Initialize database tables on startup
    init_db()
    app.state.is_started = True

    yield

    app.state.is_started = False


app = FastAPI(
    title="polyapi",
    description="A FastAPI backend for Polymarket data and trading operations",
    version = "0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health_router)
app.include_router(database_router)