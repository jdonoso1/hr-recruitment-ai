from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Import database and models to ensure SQLModel metadata is loaded
from .db import create_db_tables
from .models import Client, Job, JobStatus  # Import to ensure models are registered
from .routes import jobs, clients, hunting

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

# Serve static files (CSS, JS)
_static_dir = Path(__file__).parent.parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# Include API routers
app.include_router(jobs.router)
app.include_router(clients.router)
app.include_router(hunting.router)

# Add CORS middleware (for later frontend integration if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
