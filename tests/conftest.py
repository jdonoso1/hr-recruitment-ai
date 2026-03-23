import pytest
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool


@pytest.fixture(name="db_session")
def db_session_fixture():
    """Create in-memory SQLite database session for testing.

    Each test gets a fresh database (StaticPool for single conn).
    """
    # Import models to register them with SQLModel.metadata
    from src.app.models import Client, Job, JobStatus

    # Create in-memory SQLite engine
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    SQLModel.metadata.create_all(engine)

    # Yield session for test
    with Session(engine) as session:
        yield session


@pytest.fixture
def client_data():
    """Sample client data for tests"""
    return {
        "name": "Test Client LLC"
    }


@pytest.fixture
def job_data(client_data):
    """Sample job data for tests"""
    return {
        "client_id": 1,
        "title": "Senior Python Engineer",
        "description": "Build scalable systems with Python and FastAPI",
        "seniority": "Senior",
        "salary_min": 150000,
        "salary_max": 200000,
        "required_experience_years": 5,
        "target_industries": ["Technology", "Finance"],
        "target_company_types": ["Startup", "Tech Company"],
    }
