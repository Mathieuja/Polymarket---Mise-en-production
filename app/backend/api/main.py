"""
FastAPI application main file for the backend API.
"""


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


# routers will contain the endpoints for the API
# from .routers import  ...

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan manager.

    At startup, initializes database connections, loads configuration, etc.
    At shutdown, handles all deconnections, cleanup, etc.
    """
    # startup operations here

    yield
    
    # shutdown operations here


app = FastAPI(
    title = "polyapi",
    description = "A FastAPI backend for Polymarket data and trading operations", 
    version = "0.1.0",
    lifespan=lifespan)


# include routers when they are implemented
# app.include_router(...)