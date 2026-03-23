import os
from sqlalchemy.orm import Session
from sqlmodel import SQLModel, create_engine, Session as SQLSession
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Get database URL from environment, default to SQLite file
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hr_recruitment.db")

# Create SQLAlchemy engine
# For SQLite: add check_same_thread=False to allow multiple threads in dev
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL logging during development
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)


def create_db_tables():
    """Create all database tables defined in SQLModel models.

    Called on application startup via lifespan event in main.py.
    SQLModel.metadata.create_all uses the engine to execute CREATE TABLE if not exists.
    """
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency for database sessions.

    Usage in route:
    @app.get("/jobs")
    async def list_jobs(session: Session = Depends(get_session)):
        ...
    """
    with SQLSession(engine) as session:
        yield session
