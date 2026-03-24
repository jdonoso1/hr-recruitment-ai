"""Integration tests for hunting routes and workflows (Phase 2 Plan 02)

Tests cover:
- Start hunting session creation
- Company listing and rendering
- Candidate listing and rendering
- Candidate approval/rejection
- Company removal
- Error handling (404s, etc.)
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from unittest.mock import patch

from src.app.main import app
from src.app.models import (
    Client, Job, HuntingSession, TargetCompany, Candidate,
    JobStatus, HuntingStatus, CandidateStatus
)
from src.app.db import get_session


@pytest.fixture
def client(db_session):
    """Create a FastAPI test client with dependency injection"""
    def get_session_override():
        return db_session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def setup_job(db_session):
    """Create a test job with client"""
    client_obj = Client(name="Test Client")
    db_session.add(client_obj)
    db_session.flush()

    job = Job(
        client_id=client_obj.id,
        title="Senior Python Engineer",
        description="Build scalable systems with Python and FastAPI",
        seniority="Senior",
        salary_min=150000,
        salary_max=200000,
        target_industries=["Technology", "Finance"],
        target_company_types=["Startup", "Tech Company"],
        status=JobStatus.hunting,
    )
    db_session.add(job)
    db_session.commit()
    return job


class TestStartHunting:
    """Tests for starting a hunting session"""

    def test_start_hunting_creates_session(self, client, setup_job, db_session):
        """Test that POST /jobs/{id}/hunting/start creates a HuntingSession"""
        job_id = setup_job.id

        # Make request — use follow_redirects=False to check redirect
        response = client.post(f"/jobs/{job_id}/hunting/start", follow_redirects=False)

        # Should redirect to hunting detail page
        assert response.status_code == 303
        assert f"/jobs/{job_id}/hunting" in response.headers["location"]

        # Verify HuntingSession was created
        session = db_session.exec(
            select(HuntingSession).where(HuntingSession.job_id == job_id)
        ).first()
        assert session is not None
        # Status will be in_progress because background tasks run in test client
        assert session.status in [HuntingStatus.pending, HuntingStatus.in_progress]
        assert session.job_id == job_id

    def test_start_hunting_job_not_found(self, client, db_session):
        """Test that start_hunting returns 404 for non-existent job"""
        response = client.post("/jobs/999/hunting/start", follow_redirects=False)
        assert response.status_code == 404


class TestGetHuntingDetail:
    """Tests for the hunting detail view"""

    def test_get_hunting_detail_without_session(self, client, setup_job):
        """Test hunting detail view when no session exists"""
        job_id = setup_job.id

        response = client.get(f"/jobs/{job_id}/hunting")

        assert response.status_code == 200
        assert "Hunting for Senior Python Engineer" in response.text
        assert "Start Hunting Now" in response.text

    def test_get_hunting_detail_with_session(self, client, setup_job, db_session):
        """Test hunting detail view with an active session"""
        job_id = setup_job.id

        # Create a hunting session
        session = HuntingSession(job_id=job_id, status=HuntingStatus.in_progress)
        db_session.add(session)
        db_session.commit()

        response = client.get(f"/jobs/{job_id}/hunting")

        assert response.status_code == 200
        assert "In Progress" in response.text
        assert "Target Companies" in response.text
        assert "Candidates" in response.text

    def test_get_hunting_detail_with_companies_and_candidates(
        self, client, db_session, hunting_session_fixture, target_companies_fixture, candidates_fixture
    ):
        """Test hunting detail view renders companies and candidates"""
        # Use the fixture job
        job = db_session.exec(
            select(Job).where(Job.id == hunting_session_fixture.job_id)
        ).first()

        response = client.get(f"/jobs/{job.id}/hunting")

        assert response.status_code == 200
        # Check companies are rendered
        for company in target_companies_fixture:
            assert company.name in response.text
            assert company.industry in response.text
        # Check candidates are rendered
        for candidate in candidates_fixture:
            assert candidate.name in response.text

    def test_get_hunting_detail_job_not_found(self, client):
        """Test that hunting detail returns 404 for non-existent job"""
        response = client.get("/jobs/999/hunting")
        assert response.status_code == 404


class TestGetCompanies:
    """Tests for company listing (HTMX fragment)"""

    def test_get_companies_empty(self, client, setup_job):
        """Test companies endpoint returns empty fragment when no companies"""
        job_id = setup_job.id
        response = client.get(f"/jobs/{job_id}/hunting/companies")

        assert response.status_code == 200
        # Should show empty state
        assert "identified yet" in response.text.lower() or "no companies" in response.text.lower()

    def test_get_companies_with_data(
        self, client, db_session, hunting_session_fixture, target_companies_fixture
    ):
        """Test companies endpoint renders company cards"""
        job = db_session.exec(
            select(Job).where(Job.id == hunting_session_fixture.job_id)
        ).first()
        job_id = job.id

        response = client.get(f"/jobs/{job_id}/hunting/companies")

        assert response.status_code == 200
        # Check all companies are rendered
        for company in target_companies_fixture:
            assert company.name in response.text
            assert company.industry in response.text

    def test_get_companies_job_not_found(self, client):
        """Test companies endpoint returns 404 for non-existent job"""
        response = client.get("/jobs/999/hunting/companies")
        assert response.status_code == 404


class TestGetCandidates:
    """Tests for candidate listing (HTMX fragment)"""

    def test_get_candidates_empty(self, client, setup_job):
        """Test candidates endpoint returns empty fragment when no candidates"""
        job_id = setup_job.id
        response = client.get(f"/jobs/{job_id}/hunting/candidates")

        assert response.status_code == 200
        # Should show empty state
        assert "no candidates" in response.text.lower() or "found yet" in response.text.lower()

    def test_get_candidates_with_data(
        self, client, db_session, hunting_session_fixture, candidates_fixture
    ):
        """Test candidates endpoint renders candidate cards"""
        job = db_session.exec(
            select(Job).where(Job.id == hunting_session_fixture.job_id)
        ).first()
        job_id = job.id

        response = client.get(f"/jobs/{job_id}/hunting/candidates")

        assert response.status_code == 200
        # Check all candidates are rendered
        for candidate in candidates_fixture:
            assert candidate.name in response.text
            assert candidate.current_title in response.text

    def test_get_candidates_job_not_found(self, client):
        """Test candidates endpoint returns 404 for non-existent job"""
        response = client.get("/jobs/999/hunting/candidates")
        assert response.status_code == 404


class TestApproveCandidates:
    """Tests for candidate approval"""

    def test_approve_candidate_updates_status(
        self, client, db_session, hunting_session_fixture, candidates_fixture
    ):
        """Test that approving a candidate updates status to 'approved'"""
        candidate = candidates_fixture[1]  # Bob Smith, status=hunting
        session_id = hunting_session_fixture.id

        # Verify initial status
        assert candidate.status == CandidateStatus.hunting

        # Approve candidate
        response = client.post(
            f"/hunting/{session_id}/candidates/{candidate.id}/approve"
        )
        assert response.status_code == 200

        # Verify status changed in database
        updated = db_session.exec(
            select(Candidate).where(Candidate.id == candidate.id)
        ).first()
        assert updated.status == CandidateStatus.approved

    def test_approve_candidate_not_found(self, client, hunting_session_fixture):
        """Test that approving non-existent candidate returns 404"""
        session_id = hunting_session_fixture.id
        response = client.post(f"/hunting/{session_id}/candidates/999/approve")
        assert response.status_code == 404

    def test_approve_already_approved_candidate(
        self, client, db_session, hunting_session_fixture, candidates_fixture
    ):
        """Test that approving an already-approved candidate still works"""
        candidate = candidates_fixture[0]  # Alice, status=approved
        session_id = hunting_session_fixture.id

        # Approve (again)
        response = client.post(
            f"/hunting/{session_id}/candidates/{candidate.id}/approve"
        )
        assert response.status_code == 200

        # Status should still be approved
        updated = db_session.exec(
            select(Candidate).where(Candidate.id == candidate.id)
        ).first()
        assert updated.status == CandidateStatus.approved


class TestRejectCandidates:
    """Tests for candidate rejection"""

    def test_reject_candidate_updates_status(
        self, client, db_session, hunting_session_fixture, candidates_fixture
    ):
        """Test that rejecting a candidate updates status to 'rejected'"""
        candidate = candidates_fixture[1]  # Bob Smith, status=hunting
        session_id = hunting_session_fixture.id

        # Verify initial status
        assert candidate.status == CandidateStatus.hunting

        # Reject candidate
        response = client.post(
            f"/hunting/{session_id}/candidates/{candidate.id}/reject"
        )
        assert response.status_code == 200

        # Verify status changed in database
        updated = db_session.exec(
            select(Candidate).where(Candidate.id == candidate.id)
        ).first()
        assert updated.status == CandidateStatus.rejected

    def test_reject_candidate_not_found(self, client, hunting_session_fixture):
        """Test that rejecting non-existent candidate returns 404"""
        session_id = hunting_session_fixture.id
        response = client.post(f"/hunting/{session_id}/candidates/999/reject")
        assert response.status_code == 404

    def test_reject_already_rejected_candidate(
        self, client, db_session, hunting_session_fixture, candidates_fixture
    ):
        """Test that rejecting an already-rejected candidate still works"""
        candidate = candidates_fixture[3]  # David, status=rejected
        session_id = hunting_session_fixture.id

        # Reject (again)
        response = client.post(
            f"/hunting/{session_id}/candidates/{candidate.id}/reject"
        )
        assert response.status_code == 200

        # Status should still be rejected
        updated = db_session.exec(
            select(Candidate).where(Candidate.id == candidate.id)
        ).first()
        assert updated.status == CandidateStatus.rejected


class TestRemoveCompany:
    """Tests for company removal"""

    def test_remove_company_deletes_record(
        self, client, db_session, hunting_session_fixture, target_companies_fixture
    ):
        """Test that removing a company deletes the TargetCompany record"""
        company = target_companies_fixture[0]
        session_id = hunting_session_fixture.id

        # Verify company exists
        existing = db_session.exec(
            select(TargetCompany).where(TargetCompany.id == company.id)
        ).first()
        assert existing is not None

        # Remove company
        response = client.post(
            f"/hunting/{session_id}/companies/{company.id}/remove"
        )
        assert response.status_code == 200

        # Verify company deleted from database
        deleted = db_session.exec(
            select(TargetCompany).where(TargetCompany.id == company.id)
        ).first()
        assert deleted is None

    def test_remove_company_not_found(self, client, hunting_session_fixture):
        """Test that removing non-existent company returns 404"""
        session_id = hunting_session_fixture.id
        response = client.post(f"/hunting/{session_id}/companies/999/remove")
        assert response.status_code == 404


class TestJobDetailIntegration:
    """Integration tests for job detail page with hunting button"""

    def test_job_detail_shows_start_hunting_button(self, client, setup_job):
        """Test that job detail page includes Start Hunting button"""
        job_id = setup_job.id
        response = client.get(f"/jobs/{job_id}")

        assert response.status_code == 200
        assert "Start Hunting" in response.text
        assert f'href="/jobs/{job_id}/hunting"' in response.text
