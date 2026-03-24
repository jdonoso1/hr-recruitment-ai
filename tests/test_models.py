"""Tests for SQLModel data models (Client, Job, HuntingSession, Candidate, Outreach)"""

from src.app.models import (
    Client, Job, JobStatus,
    HuntingSession, HuntingStatus,
    TargetCompany,
    Candidate, CandidateStatus,
    OutreachDraft, OutreachStatus,
)


def test_client_model_creation(db_session):
    """Test Client model creation"""
    client = Client(name="Test Client")
    db_session.add(client)
    db_session.commit()

    retrieved = db_session.query(Client).filter(Client.name == "Test Client").first()
    assert retrieved is not None
    assert retrieved.name == "Test Client"


def test_job_model_creation(db_session):
    """Test Job model creation with all fields"""
    client = Client(name="Test Client")
    db_session.add(client)
    db_session.flush()

    job = Job(
        client_id=client.id,
        title="Senior Python Engineer",
        description="Build scalable systems",
        seniority="Senior",
        salary_min=150000,
        salary_max=200000,
        target_industries=["Technology", "Finance"],
        target_company_types=["Startup"],
        status=JobStatus.hunting,
    )
    db_session.add(job)
    db_session.commit()

    retrieved = db_session.query(Job).filter(Job.title == "Senior Python Engineer").first()
    assert retrieved is not None
    assert retrieved.target_industries == ["Technology", "Finance"]


def test_hunting_session_creation(db_session, hunting_session_fixture):
    """Test HuntingSession model creation"""
    session = db_session.query(HuntingSession).first()
    assert session is not None
    assert session.status == HuntingStatus.pending


def test_target_company_creation(db_session, target_companies_fixture):
    """Test TargetCompany model creation"""
    companies = db_session.query(TargetCompany).all()
    assert len(companies) == 3
    assert companies[0].name == "Tech Startup Inc"
    assert companies[0].industry == "Technology"


def test_candidate_creation(db_session, candidates_fixture):
    """Test Candidate model creation with mixed statuses"""
    candidates = db_session.query(Candidate).all()
    assert len(candidates) == 5

    approved = db_session.query(Candidate).filter(Candidate.status == CandidateStatus.approved).all()
    assert len(approved) == 2

    rejected = db_session.query(Candidate).filter(Candidate.status == CandidateStatus.rejected).all()
    assert len(rejected) == 1


def test_candidate_status_enum():
    """Test CandidateStatus enum values"""
    assert CandidateStatus.hunting.value == "hunting"
    assert CandidateStatus.approved.value == "approved"
    assert CandidateStatus.rejected.value == "rejected"


def test_hunting_status_enum():
    """Test HuntingStatus enum values"""
    assert HuntingStatus.pending.value == "pending"
    assert HuntingStatus.in_progress.value == "in_progress"
    assert HuntingStatus.completed.value == "completed"
    assert HuntingStatus.failed.value == "failed"


def test_outreach_status_enum():
    """Test OutreachStatus enum values"""
    assert OutreachStatus.pending_review.value == "pending_review"
    assert OutreachStatus.approved.value == "approved"
    assert OutreachStatus.sent.value == "sent"
    assert OutreachStatus.replied.value == "replied"
    assert OutreachStatus.not_interested.value == "not_interested"
    assert OutreachStatus.error.value == "error"


def test_outreach_draft_creation(db_session, candidates_fixture, hunting_session_fixture):
    """Test OutreachDraft model creation"""
    # Get first candidate
    candidate = candidates_fixture[0]

    # Get a job from the hunting session
    from sqlmodel import select
    job_statement = select(Job)
    jobs = db_session.exec(job_statement).all()
    job = jobs[0]

    draft = OutreachDraft(
        candidate_id=candidate.id,
        job_id=job.id,
        linkedin_message="Hi, I found you and I'm interested in talking.",
        email_message="Dear candidate, we have an exciting opportunity...",
        status=OutreachStatus.pending_review,
    )
    db_session.add(draft)
    db_session.commit()

    retrieved = db_session.query(OutreachDraft).filter(OutreachDraft.candidate_id == candidate.id).first()
    assert retrieved is not None
    assert retrieved.status == OutreachStatus.pending_review
    assert len(retrieved.linkedin_message) > 0
