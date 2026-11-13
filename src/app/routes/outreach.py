"""Outreach routes — Draft generation, consultant review, and send queue (Phase 2 Plan 03)

Status flow (OutreachStatus):
    pending_review ──approve──▶ approved ──send──▶ sent ──▶ replied | not_interested
          │                        │
          └────────discard─────────┴──▶ discarded

Routes:
- POST /outreach/generate                  — Draft outreach for approved candidates (background)
- GET  /jobs/{job_id}/outreach/drafts      — Draft review page (filter with ?status=)
- GET  /jobs/{job_id}/outreach/drafts/list — Draft list fragment (HTMX polling while generating)
- GET  /jobs/{job_id}/outreach/queue       — Queue & status page
- POST /outreach/{draft_id}/edit           — Save edited messages (pending_review only)
- POST /outreach/{draft_id}/approve        — pending_review → approved
- POST /outreach/{draft_id}/discard        — pending_review|approved → discarded
- POST /outreach/{draft_id}/status         — sent → replied | not_interested
- POST /outreach/queue/send                — approved → sent for one job
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from ..agents.outreach_drafter import (
    EMAIL_MAX_CHARS,
    LINKEDIN_MAX_CHARS,
    CandidateSummary,
    JobSummary,
    OutreachDrafterAgent,
    OutreachDrafterRequest,
    OutreachDrafterResponse,
    TargetCompanySummary,
    build_template_draft,
)
from ..db import get_session
from ..models import (
    Candidate,
    CandidateStatus,
    HuntingSession,
    Job,
    OutreachDraft,
    OutreachStatus,
    TargetCompany,
    utcnow,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["outreach"])

templates_dir = Path(__file__).parent.parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))
templates.env.cache = None

# Drafts in these states count as "this candidate already has outreach"
ACTIVE_STATUSES = [s for s in OutreachStatus if s != OutreachStatus.discarded]
QUEUE_STATUSES = [
    OutreachStatus.approved,
    OutreachStatus.sent,
    OutreachStatus.replied,
    OutreachStatus.not_interested,
    OutreachStatus.error,
]
DRAFT_FILTERS = {
    "all": ACTIVE_STATUSES,
    "pending_review": [OutreachStatus.pending_review],
    "approved": [OutreachStatus.approved],
    "sent": [OutreachStatus.sent, OutreachStatus.replied, OutreachStatus.not_interested],
}
HTMX_STOP_POLLING = 286  # htmx stops an `every Ns` trigger on this status


@dataclass
class DraftItem:
    """A draft plus the candidate it is for, as rendered by the templates."""
    draft: OutreachDraft
    candidate: Candidate


# ===== Helpers =====

def _get_job_or_404(job_id: int, session: Session) -> Job:
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _get_draft_or_404(draft_id: int, session: Session) -> OutreachDraft:
    draft = session.get(OutreachDraft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


def _require_status(draft: OutreachDraft, allowed: List[OutreachStatus], action: str) -> None:
    if draft.status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot {action} a draft with status '{draft.status.value}'",
        )


def candidates_awaiting_outreach(
    job_id: int, session: Session, hunting_session_id: Optional[int] = None
) -> List[Candidate]:
    """Approved candidates for this job that have no active (non-discarded) draft."""
    query = (
        select(Candidate)
        .join(HuntingSession, Candidate.hunting_session_id == HuntingSession.id)
        .where(HuntingSession.job_id == job_id)
        .where(Candidate.status == CandidateStatus.approved)
    )
    if hunting_session_id is not None:
        query = query.where(Candidate.hunting_session_id == hunting_session_id)

    has_draft = set(
        session.exec(
            select(OutreachDraft.candidate_id)
            .where(OutreachDraft.job_id == job_id)
            .where(OutreachDraft.status.in_(ACTIVE_STATUSES))
        ).all()
    )
    return [c for c in session.exec(query.order_by(Candidate.id)).all() if c.id not in has_draft]


def outreach_summary(job_id: int, session: Session) -> dict:
    """Counts used by the job detail sidebar."""
    statuses = session.exec(
        select(OutreachDraft.status)
        .where(OutreachDraft.job_id == job_id)
        .where(OutreachDraft.status.in_(ACTIVE_STATUSES))
    ).all()
    return {
        "awaiting_outreach_count": len(candidates_awaiting_outreach(job_id, session)),
        "draft_count": len(statuses),
        "approved_draft_count": sum(1 for s in statuses if s == OutreachStatus.approved),
    }


def _load_drafts(job_id: int, statuses: List[OutreachStatus], session: Session) -> List[DraftItem]:
    rows = session.exec(
        select(OutreachDraft, Candidate)
        .join(Candidate, OutreachDraft.candidate_id == Candidate.id)
        .where(OutreachDraft.job_id == job_id)
        .where(OutreachDraft.status.in_(statuses))
        .order_by(OutreachDraft.created_at.desc(), OutreachDraft.id.desc())
    ).all()
    return [DraftItem(draft=d, candidate=c) for d, c in rows]


def _draft_counts(job_id: int, session: Session) -> dict:
    statuses = session.exec(
        select(OutreachDraft.status)
        .where(OutreachDraft.job_id == job_id)
        .where(OutreachDraft.status.in_(ACTIVE_STATUSES))
    ).all()
    return {key: sum(1 for s in statuses if s in allowed) for key, allowed in DRAFT_FILTERS.items()}


def _build_request(job: Job, candidate: Candidate, company: Optional[TargetCompany]) -> OutreachDrafterRequest:
    return OutreachDrafterRequest(
        job=JobSummary(
            id=job.id,
            title=job.title,
            description=job.description,
            seniority=job.seniority,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            required_experience_years=job.required_experience_years,
        ),
        candidate=CandidateSummary(
            name=candidate.name,
            current_title=candidate.current_title,
            current_company=candidate.current_company,
            linkedin_url=candidate.linkedin_url,
        ),
        company=TargetCompanySummary(
            name=company.name if company else candidate.current_company,
            industry=company.industry if company else "Unknown",
            size_description=company.size_description if company else "Unknown",
        ),
    )


async def _draft_all(requests: List[OutreachDrafterRequest]) -> List[OutreachDrafterResponse]:
    """Draft every request concurrently; fall back to a template draft per failure."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        logger.warning("ANTHROPIC_API_KEY not set; using template outreach drafts")
        return [build_template_draft(r) for r in requests]

    agent = OutreachDrafterAgent()
    responses = await asyncio.gather(*(agent.run(r) for r in requests))
    results = []
    for req, resp in zip(requests, responses):
        if resp.status == "success":
            results.append(resp.data)
        else:
            logger.warning("OutreachDrafterAgent failed for %s: %s", req.candidate.name, resp.error)
            results.append(build_template_draft(req))
    return results


def generate_drafts_task(job_id: int, candidate_ids: List[int], bind) -> None:
    """Background task: draft outreach and store OutreachDraft records (pending_review)."""
    with Session(bind) as bg_session:
        job = bg_session.get(Job, job_id)
        if not job:
            return

        # Re-check inside the task so a double click can't create duplicates
        eligible_ids = {c.id for c in candidates_awaiting_outreach(job_id, bg_session)}
        candidates = [bg_session.get(Candidate, cid) for cid in candidate_ids if cid in eligible_ids]
        if not candidates:
            return

        requests = [
            _build_request(job, c, bg_session.get(TargetCompany, c.target_company_id))
            for c in candidates
        ]
        drafts = asyncio.run(_draft_all(requests))

        for candidate, drafted in zip(candidates, drafts):
            bg_session.add(OutreachDraft(
                candidate_id=candidate.id,
                job_id=job_id,
                linkedin_message=drafted.linkedin_message,
                email_message=drafted.email_message,
                status=OutreachStatus.pending_review,
            ))
        bg_session.commit()


def _render_card(request: Request, draft: OutreachDraft, session: Session) -> HTMLResponse:
    candidate = session.get(Candidate, draft.candidate_id)
    return templates.TemplateResponse(request, "jobs/outreach-draft-card.html", {
        "item": DraftItem(draft=draft, candidate=candidate),
        "linkedin_max": LINKEDIN_MAX_CHARS,
        "email_max": EMAIL_MAX_CHARS,
    })


# ===== Generation =====

@router.post("/outreach/generate")
def generate_outreach(
    background_tasks: BackgroundTasks,
    job_id: int = Form(...),
    hunting_session_id: Optional[int] = Form(None),
    session: Session = Depends(get_session),
):
    """Queue draft generation for approved candidates, then go to the drafts page."""
    _get_job_or_404(job_id, session)

    if hunting_session_id is not None:
        hunting_session = session.get(HuntingSession, hunting_session_id)
        if not hunting_session or hunting_session.job_id != job_id:
            raise HTTPException(status_code=404, detail="Hunting session not found")

    candidates = candidates_awaiting_outreach(job_id, session, hunting_session_id)
    if candidates:
        background_tasks.add_task(
            generate_drafts_task, job_id, [c.id for c in candidates], session.get_bind()
        )

    url = f"/jobs/{job_id}/outreach/drafts"
    if candidates:
        url += f"?generating={len(candidates)}"
    return RedirectResponse(url=url, status_code=303)


# ===== Pages =====

@router.get("/jobs/{job_id}/outreach/drafts", response_class=HTMLResponse)
def outreach_drafts_page(
    job_id: int,
    request: Request,
    status: str = "all",
    generating: int = 0,
    session: Session = Depends(get_session),
):
    job = _get_job_or_404(job_id, session)
    if status not in DRAFT_FILTERS:
        status = "all"

    return templates.TemplateResponse(request, "jobs/outreach-drafts.html", {
        "job": job,
        "items": _load_drafts(job_id, DRAFT_FILTERS[status], session),
        "counts": _draft_counts(job_id, session),
        "active_filter": status,
        "generating": generating,
        "awaiting_count": len(candidates_awaiting_outreach(job_id, session)),
        "linkedin_max": LINKEDIN_MAX_CHARS,
        "email_max": EMAIL_MAX_CHARS,
    })


@router.get("/jobs/{job_id}/outreach/drafts/list", response_class=HTMLResponse)
def outreach_drafts_list(
    job_id: int,
    request: Request,
    status: str = "all",
    session: Session = Depends(get_session),
):
    """Draft list fragment. Returns 286 (stop polling) once nothing is left to generate."""
    _get_job_or_404(job_id, session)
    if status not in DRAFT_FILTERS:
        status = "all"

    response = templates.TemplateResponse(request, "jobs/outreach-drafts-list.html", {
        "items": _load_drafts(job_id, DRAFT_FILTERS[status], session),
        "linkedin_max": LINKEDIN_MAX_CHARS,
        "email_max": EMAIL_MAX_CHARS,
    })
    if not candidates_awaiting_outreach(job_id, session):
        response.status_code = HTMX_STOP_POLLING
    return response


@router.get("/jobs/{job_id}/outreach/queue", response_class=HTMLResponse)
def outreach_queue_page(
    job_id: int,
    request: Request,
    sent: int = 0,
    session: Session = Depends(get_session),
):
    job = _get_job_or_404(job_id, session)
    items = _load_drafts(job_id, QUEUE_STATUSES, session)
    return templates.TemplateResponse(request, "jobs/outreach-queue.html", {
        "job": job,
        "items": items,
        "approved_count": sum(1 for i in items if i.draft.status == OutreachStatus.approved),
        "just_sent": sent,
    })


# ===== Draft actions =====

@router.post("/outreach/{draft_id}/edit", response_class=HTMLResponse)
def edit_draft(
    draft_id: int,
    request: Request,
    linkedin_message: str = Form(...),
    email_message: str = Form(...),
    session: Session = Depends(get_session),
):
    draft = _get_draft_or_404(draft_id, session)
    _require_status(draft, [OutreachStatus.pending_review], "edit")

    linkedin_message, email_message = linkedin_message.strip(), email_message.strip()
    if not linkedin_message or not email_message:
        raise HTTPException(status_code=400, detail="Messages cannot be empty")
    if len(linkedin_message) > LINKEDIN_MAX_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"LinkedIn message is {len(linkedin_message)} characters (max {LINKEDIN_MAX_CHARS})",
        )
    if len(email_message) > EMAIL_MAX_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Email is {len(email_message)} characters (max {EMAIL_MAX_CHARS})",
        )

    draft.linkedin_message = linkedin_message
    draft.email_message = email_message
    draft.updated_at = utcnow()
    session.add(draft)
    session.commit()
    session.refresh(draft)
    return _render_card(request, draft, session)


@router.post("/outreach/{draft_id}/approve", response_class=HTMLResponse)
def approve_draft(draft_id: int, request: Request, session: Session = Depends(get_session)):
    draft = _get_draft_or_404(draft_id, session)
    _require_status(draft, [OutreachStatus.pending_review], "approve")

    draft.status = OutreachStatus.approved
    draft.updated_at = utcnow()
    session.add(draft)
    session.commit()
    session.refresh(draft)
    return _render_card(request, draft, session)


@router.post("/outreach/{draft_id}/discard")
def discard_draft(draft_id: int, session: Session = Depends(get_session)):
    """Discard a draft. Returns an empty body so HTMX removes the card."""
    draft = _get_draft_or_404(draft_id, session)
    _require_status(draft, [OutreachStatus.pending_review, OutreachStatus.approved], "discard")

    draft.status = OutreachStatus.discarded
    draft.updated_at = utcnow()
    session.add(draft)
    session.commit()
    return Response(status_code=200)


@router.post("/outreach/{draft_id}/status", response_class=HTMLResponse)
def update_reply_status(
    draft_id: int,
    request: Request,
    status: str = Form(...),
    session: Session = Depends(get_session),
):
    """Record the candidate's response to a sent message."""
    draft = _get_draft_or_404(draft_id, session)
    allowed = {OutreachStatus.replied.value, OutreachStatus.not_interested.value}
    if status not in allowed:
        raise HTTPException(status_code=400, detail=f"Status must be one of {sorted(allowed)}")
    _require_status(draft, [OutreachStatus.sent], "update the reply status of")

    draft.status = OutreachStatus(status)
    draft.updated_at = utcnow()
    session.add(draft)
    session.commit()
    session.refresh(draft)

    candidate = session.get(Candidate, draft.candidate_id)
    return templates.TemplateResponse(request, "jobs/outreach-queue-card.html", {
        "item": DraftItem(draft=draft, candidate=candidate),
    })


@router.post("/outreach/queue/send")
def send_approved(job_id: int = Form(...), session: Session = Depends(get_session)):
    """Mark every approved draft for this job as sent.

    PLACEHOLDER — no messages are delivered yet. When a LinkedIn / email provider
    is integrated, the actual send happens here and failures set status=error.
    """
    _get_job_or_404(job_id, session)
    drafts = session.exec(
        select(OutreachDraft)
        .where(OutreachDraft.job_id == job_id)
        .where(OutreachDraft.status == OutreachStatus.approved)
    ).all()

    now = utcnow()
    for draft in drafts:
        draft.status = OutreachStatus.sent
        draft.sent_at = now
        draft.updated_at = now
        session.add(draft)
    session.commit()

    return RedirectResponse(url=f"/jobs/{job_id}/outreach/queue?sent={len(drafts)}", status_code=303)
