import pytest
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool


@pytest.fixture(name="db_session")
def db_session_fixture():
    """Create in-memory SQLite database session for testing.

    Each test gets a fresh database (StaticPool for single conn).
    """
    # Import models to register them with SQLModel.metadata
    from src.app.models import (
        Client, Job, JobStatus, HuntingSession, TargetCompany,
        Candidate, OutreachDraft, HuntingStatus, CandidateStatus, OutreachStatus
    )

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


@pytest.fixture
def hunting_session_fixture(db_session):
    """Create a HuntingSession record linked to a job"""
    from src.app.models import Client, Job, HuntingSession, HuntingStatus

    # Create a client
    client = Client(name="Test Client LLC")
    db_session.add(client)
    db_session.flush()

    # Create a job
    job = Job(
        client_id=client.id,
        title="Senior Python Engineer",
        description="Build scalable systems with Python and FastAPI",
        seniority="Senior",
        salary_min=150000,
        salary_max=200000,
        target_industries=["Technology", "Finance"],
        target_company_types=["Startup", "Tech Company"],
    )
    db_session.add(job)
    db_session.flush()

    # Create a hunting session
    session = HuntingSession(
        job_id=job.id,
        status=HuntingStatus.pending,
    )
    db_session.add(session)
    db_session.commit()

    return session


@pytest.fixture
def target_companies_fixture(db_session, hunting_session_fixture):
    """Create 3 TargetCompany records linked to hunting session"""
    from src.app.models import TargetCompany

    companies = [
        TargetCompany(
            hunting_session_id=hunting_session_fixture.id,
            name="Tech Startup Inc",
            industry="Technology",
            size_description="50-200 employees",
            linkedin_url="https://linkedin.com/company/tech-startup",
        ),
        TargetCompany(
            hunting_session_id=hunting_session_fixture.id,
            name="Finance Corp LLC",
            industry="Finance",
            size_description="200-500 employees",
            linkedin_url="https://linkedin.com/company/finance-corp",
        ),
        TargetCompany(
            hunting_session_id=hunting_session_fixture.id,
            name="Scale-Up Labs",
            industry="Technology",
            size_description="100-300 employees",
            linkedin_url="https://linkedin.com/company/scale-up-labs",
        ),
    ]

    for company in companies:
        db_session.add(company)
    db_session.commit()

    return companies


@pytest.fixture
def candidates_fixture(db_session, hunting_session_fixture, target_companies_fixture):
    """Create 5 Candidate records with mixed statuses"""
    from src.app.models import Candidate, CandidateStatus

    candidates = [
        Candidate(
            hunting_session_id=hunting_session_fixture.id,
            target_company_id=target_companies_fixture[0].id,
            name="Alice Johnson",
            current_title="Senior Engineer",
            current_company="Tech Startup Inc",
            email="alice@techstartup.com",
            linkedin_url="https://linkedin.com/in/alice-johnson",
            status=CandidateStatus.approved,
        ),
        Candidate(
            hunting_session_id=hunting_session_fixture.id,
            target_company_id=target_companies_fixture[0].id,
            name="Bob Smith",
            current_title="Staff Engineer",
            current_company="Tech Startup Inc",
            email="bob@techstartup.com",
            linkedin_url="https://linkedin.com/in/bob-smith",
            status=CandidateStatus.hunting,
        ),
        Candidate(
            hunting_session_id=hunting_session_fixture.id,
            target_company_id=target_companies_fixture[1].id,
            name="Carol Davis",
            current_title="Engineering Manager",
            current_company="Finance Corp LLC",
            email="carol@financecorp.com",
            linkedin_url="https://linkedin.com/in/carol-davis",
            status=CandidateStatus.approved,
        ),
        Candidate(
            hunting_session_id=hunting_session_fixture.id,
            target_company_id=target_companies_fixture[1].id,
            name="David Wilson",
            current_title="Senior Developer",
            current_company="Finance Corp LLC",
            email="david@financecorp.com",
            linkedin_url="https://linkedin.com/in/david-wilson",
            status=CandidateStatus.rejected,
        ),
        Candidate(
            hunting_session_id=hunting_session_fixture.id,
            target_company_id=target_companies_fixture[2].id,
            name="Emma Brown",
            current_title="Tech Lead",
            current_company="Scale-Up Labs",
            email="emma@scaleuplabs.com",
            linkedin_url="https://linkedin.com/in/emma-brown",
            status=CandidateStatus.hunting,
        ),
    ]

    for candidate in candidates:
        db_session.add(candidate)
    db_session.commit()

    return candidates
