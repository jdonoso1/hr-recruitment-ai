"""Integration tests for outreach routes (Phase 2 Plan 03).

Uses the shared fixtures in conftest.py: hunting_session_fixture creates a job, and
candidates_fixture adds 5 candidates, of which Alice Johnson and Carol Davis are approved.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from src.app.agents.base import AgentResponse
from src.app.agents.outreach_drafter import (
    EMAIL_MAX_CHARS,
    LINKEDIN_MAX_CHARS,
    TEMPLATE_NOTE,
    OutreachDrafterResponse,
)
from src.app.db import get_session
from src.app.main import app
from src.app.models import HuntingSession, Job, OutreachDraft, OutreachStatus


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def job_id(hunting_session_fixture):
    return hunting_session_fixture.job_id


@pytest.fixture
def approved_candidates(candidates_fixture):
    return [c for c in candidates_fixture if c.status == "approved"]


@pytest.fixture
def drafts(db_session, job_id, approved_candidates):
    """One pending_review draft per approved candidate."""
    created = []
    for candidate in approved_candidates:
        draft = OutreachDraft(
            candidate_id=candidate.id,
            job_id=job_id,
            linkedin_message=f"Hi {candidate.name.split()[0]}, open to exploring a new role?",
            email_message=f"Subject: Opportunity\n\nHi {candidate.name.split()[0]}, interested?",
            status=OutreachStatus.pending_review,
        )
        db_session.add(draft)
        created.append(draft)
    db_session.commit()
    return created


def _set_status(db_session, draft, status):
    draft.status = status
    db_session.add(draft)
    db_session.commit()


def _fake_agent_run(text="AI drafted"):
    async def run(self, request):
        name = request.candidate.name
        return AgentResponse(status="success", data=OutreachDrafterResponse(
            linkedin_message=f"{text} LinkedIn for {name}",
            email_message=f"{text} email for {name}",
        ))
    return run


class TestGenerate:
    def test_creates_pending_draft_per_approved_candidate(
        self, client, db_session, job_id, approved_candidates, monkeypatch
    ):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        with patch("src.app.routes.outreach.OutreachDrafterAgent.run", _fake_agent_run()):
            response = client.post("/outreach/generate", data={"job_id": job_id}, follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == f"/jobs/{job_id}/outreach/drafts?generating=2"

        created = db_session.exec(select(OutreachDraft).where(OutreachDraft.job_id == job_id)).all()
        assert {d.candidate_id for d in created} == {c.id for c in approved_candidates}
        assert all(d.status == OutreachStatus.pending_review for d in created)
        assert all(d.linkedin_message.startswith("AI drafted") for d in created)

    def test_falls_back_to_template_when_agent_fails(self, client, db_session, job_id, approved_candidates, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        failing = AsyncMock(return_value=AgentResponse(status="error", error="boom"))
        with patch("src.app.routes.outreach.OutreachDrafterAgent.run", failing):
            client.post("/outreach/generate", data={"job_id": job_id})

        created = db_session.exec(select(OutreachDraft)).all()
        assert len(created) == 2
        assert all(TEMPLATE_NOTE in d.linkedin_message for d in created)

    def test_uses_template_without_api_key(self, client, db_session, job_id, approved_candidates, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with patch("src.app.routes.outreach.OutreachDrafterAgent.run") as run:
            client.post("/outreach/generate", data={"job_id": job_id})
        run.assert_not_called()

        created = db_session.exec(select(OutreachDraft)).all()
        assert len(created) == 2
        assert all(TEMPLATE_NOTE in d.email_message for d in created)

    def test_skips_candidates_that_already_have_drafts(self, client, db_session, job_id, drafts):
        response = client.post("/outreach/generate", data={"job_id": job_id}, follow_redirects=False)

        assert response.headers["location"] == f"/jobs/{job_id}/outreach/drafts"
        assert len(db_session.exec(select(OutreachDraft)).all()) == 2

    def test_regenerates_after_discard(self, client, db_session, job_id, drafts, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        _set_status(db_session, drafts[0], OutreachStatus.discarded)

        client.post("/outreach/generate", data={"job_id": job_id})

        active = db_session.exec(
            select(OutreachDraft).where(OutreachDraft.status == OutreachStatus.pending_review)
        ).all()
        assert len(active) == 2
        assert drafts[0].candidate_id in {d.candidate_id for d in active}

    def test_job_not_found(self, client):
        assert client.post("/outreach/generate", data={"job_id": 999}).status_code == 404

    def test_hunting_session_must_belong_to_job(self, client, db_session, job_id, candidates_fixture):
        other_job = Job(client_id=1, title="Other", description="x", seniority="Junior")
        db_session.add(other_job)
        db_session.commit()
        other_session = HuntingSession(job_id=other_job.id)
        db_session.add(other_session)
        db_session.commit()

        response = client.post(
            "/outreach/generate",
            data={"job_id": job_id, "hunting_session_id": other_session.id},
        )
        assert response.status_code == 404


class TestDraftsPage:
    def test_renders_draft_cards(self, client, job_id, drafts):
        response = client.get(f"/jobs/{job_id}/outreach/drafts")

        assert response.status_code == 200
        assert "Outreach Drafts for Senior Python Engineer" in response.text
        assert "Alice Johnson" in response.text
        assert "Carol Davis" in response.text
        assert "badge-pending_review" in response.text
        assert f'hx-post="/outreach/{drafts[0].id}/approve"' in response.text

    def test_status_filter(self, client, db_session, job_id, drafts):
        _set_status(db_session, drafts[0], OutreachStatus.approved)

        response = client.get(f"/jobs/{job_id}/outreach/drafts?status=approved")

        assert f'id="draft-{drafts[0].id}"' in response.text
        assert f'id="draft-{drafts[1].id}"' not in response.text

    def test_discarded_drafts_are_hidden(self, client, db_session, job_id, drafts):
        _set_status(db_session, drafts[0], OutreachStatus.discarded)
        response = client.get(f"/jobs/{job_id}/outreach/drafts")
        assert f'id="draft-{drafts[0].id}"' not in response.text

    def test_empty_state(self, client, job_id):
        response = client.get(f"/jobs/{job_id}/outreach/drafts")
        assert response.status_code == 200
        assert "No drafts here" in response.text

    def test_list_fragment_stops_polling_when_done(self, client, job_id, drafts):
        response = client.get(f"/jobs/{job_id}/outreach/drafts/list")
        assert response.status_code == 286
        assert "Alice Johnson" in response.text

    def test_list_fragment_keeps_polling_while_candidates_await_drafts(self, client, job_id, candidates_fixture):
        assert client.get(f"/jobs/{job_id}/outreach/drafts/list").status_code == 200

    def test_job_not_found(self, client):
        assert client.get("/jobs/999/outreach/drafts").status_code == 404


class TestDraftActions:
    def test_approve(self, client, db_session, drafts):
        response = client.post(f"/outreach/{drafts[0].id}/approve")

        assert response.status_code == 200
        assert "badge-approved" in response.text
        db_session.refresh(drafts[0])
        assert drafts[0].status == OutreachStatus.approved

    def test_cannot_approve_twice(self, client, db_session, drafts):
        _set_status(db_session, drafts[0], OutreachStatus.approved)
        assert client.post(f"/outreach/{drafts[0].id}/approve").status_code == 409

    def test_discard(self, client, db_session, drafts):
        response = client.post(f"/outreach/{drafts[0].id}/discard")

        assert response.status_code == 200
        assert response.text == ""
        db_session.refresh(drafts[0])
        assert drafts[0].status == OutreachStatus.discarded

    def test_cannot_discard_sent(self, client, db_session, drafts):
        _set_status(db_session, drafts[0], OutreachStatus.sent)
        assert client.post(f"/outreach/{drafts[0].id}/discard").status_code == 409

    def test_edit(self, client, db_session, drafts):
        response = client.post(f"/outreach/{drafts[0].id}/edit", data={
            "linkedin_message": "  Edited LinkedIn  ",
            "email_message": "Edited email",
        })

        assert response.status_code == 200
        assert "Edited LinkedIn" in response.text
        db_session.refresh(drafts[0])
        assert drafts[0].linkedin_message == "Edited LinkedIn"
        assert drafts[0].email_message == "Edited email"
        assert drafts[0].status == OutreachStatus.pending_review

    @pytest.mark.parametrize("field,limit", [
        ("linkedin_message", LINKEDIN_MAX_CHARS),
        ("email_message", EMAIL_MAX_CHARS),
    ])
    def test_edit_rejects_overlong_message(self, client, db_session, drafts, field, limit):
        data = {"linkedin_message": "ok", "email_message": "ok", field: "x" * (limit + 1)}
        response = client.post(f"/outreach/{drafts[0].id}/edit", data=data)

        assert response.status_code == 400
        assert f"max {limit}" in response.json()["detail"]
        db_session.refresh(drafts[0])
        assert drafts[0].linkedin_message.startswith("Hi Alice")

    def test_edit_rejects_blank_message(self, client, drafts):
        response = client.post(f"/outreach/{drafts[0].id}/edit", data={
            "linkedin_message": "   ", "email_message": "ok",
        })
        assert response.status_code == 400

    def test_cannot_edit_approved(self, client, db_session, drafts):
        _set_status(db_session, drafts[0], OutreachStatus.approved)
        response = client.post(f"/outreach/{drafts[0].id}/edit", data={
            "linkedin_message": "a", "email_message": "b",
        })
        assert response.status_code == 409

    @pytest.mark.parametrize("action", ["approve", "discard"])
    def test_draft_not_found(self, client, action):
        assert client.post(f"/outreach/999/{action}").status_code == 404

    def test_edit_draft_not_found(self, client):
        response = client.post("/outreach/999/edit", data={"linkedin_message": "a", "email_message": "b"})
        assert response.status_code == 404


class TestQueue:
    def test_queue_page_shows_approved_with_send_button(self, client, db_session, job_id, drafts):
        _set_status(db_session, drafts[0], OutreachStatus.approved)

        response = client.get(f"/jobs/{job_id}/outreach/queue")

        assert response.status_code == 200
        assert "Alice Johnson" in response.text
        assert "Carol Davis" not in response.text  # still pending review
        assert "Send 1 Approved Message" in response.text

    def test_queue_empty_state(self, client, job_id, drafts):
        response = client.get(f"/jobs/{job_id}/outreach/queue")
        assert "No approved drafts yet" in response.text
        assert "Approved Message" not in response.text

    def test_send_marks_approved_as_sent(self, client, db_session, job_id, drafts):
        _set_status(db_session, drafts[0], OutreachStatus.approved)

        response = client.post("/outreach/queue/send", data={"job_id": job_id}, follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == f"/jobs/{job_id}/outreach/queue?sent=1"
        db_session.refresh(drafts[0])
        db_session.refresh(drafts[1])
        assert drafts[0].status == OutreachStatus.sent
        assert drafts[0].sent_at is not None
        assert drafts[1].status == OutreachStatus.pending_review
        assert drafts[1].sent_at is None

    def test_send_only_affects_given_job(self, client, db_session, job_id, drafts):
        other_job = Job(client_id=1, title="Other", description="x", seniority="Junior")
        db_session.add(other_job)
        db_session.commit()
        other_draft = OutreachDraft(
            candidate_id=drafts[0].candidate_id, job_id=other_job.id,
            linkedin_message="a", email_message="b", status=OutreachStatus.approved,
        )
        db_session.add(other_draft)
        db_session.commit()

        client.post("/outreach/queue/send", data={"job_id": job_id})

        db_session.refresh(other_draft)
        assert other_draft.status == OutreachStatus.approved

    @pytest.mark.parametrize("status", ["replied", "not_interested"])
    def test_mark_reply_status(self, client, db_session, drafts, status):
        _set_status(db_session, drafts[0], OutreachStatus.sent)

        response = client.post(f"/outreach/{drafts[0].id}/status", data={"status": status})

        assert response.status_code == 200
        assert f"badge-{status}" in response.text
        db_session.refresh(drafts[0])
        assert drafts[0].status == OutreachStatus(status)

    def test_reply_status_requires_sent(self, client, drafts):
        response = client.post(f"/outreach/{drafts[0].id}/status", data={"status": "replied"})
        assert response.status_code == 409

    def test_reply_status_rejects_invalid_value(self, client, db_session, drafts):
        _set_status(db_session, drafts[0], OutreachStatus.sent)
        response = client.post(f"/outreach/{drafts[0].id}/status", data={"status": "approved"})
        assert response.status_code == 400


class TestJobDetailIntegration:
    def test_shows_generate_button_for_approved_candidates(self, client, job_id, candidates_fixture):
        response = client.get(f"/jobs/{job_id}")
        assert "Generate Outreach (2 candidates)" in response.text
        assert "View Outreach Drafts" not in response.text

    def test_shows_draft_links_once_drafted(self, client, db_session, job_id, drafts):
        _set_status(db_session, drafts[0], OutreachStatus.approved)
        response = client.get(f"/jobs/{job_id}")

        assert "Generate Outreach" not in response.text
        assert "View Outreach Drafts (2)" in response.text
        assert "Outreach Queue (1 ready)" in response.text
