from contextlib import asynccontextmanager
from fastapi import FastAPI
from pathlib import Path

# Import database and models to ensure SQLModel metadata is loaded
from .db import create_db_tables
from .models import Client, Job, JobStatus  # Import to ensure models are registered

# Lifespan event to create database tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create database tables
    create_db_tables()
    print("Database tables initialized on startup")
    yield
    # Shutdown: cleanup if needed
    print("Application shutting down")

# Create FastAPI app with lifespan event
app = FastAPI(
    title="HR Recruitment AI",
    description="AI-powered recruitment platform for consultants",
    version="0.1.0",
    lifespan=lifespan,
)

# Health check endpoint
@app.get("/health")
async def health():
    """Simple health check endpoint"""
    return {"status": "ok", "message": "HR Recruitment AI API is running"}

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "app": "HR Recruitment AI",
        "version": "0.1.0",
        "docs": "/docs",
    }
