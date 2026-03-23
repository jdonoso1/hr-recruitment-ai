from contextlib import asynccontextmanager
from fastapi import FastAPI
from pathlib import Path

from .db import create_db_tables

# Lifespan event to create tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create database tables
    create_db_tables()
    yield
    # Shutdown: nothing for now

app = FastAPI(title="HR Recruitment AI", lifespan=lifespan)

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "ok"}
