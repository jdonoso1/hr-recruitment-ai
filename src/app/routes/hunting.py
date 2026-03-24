"""Hunting routes — Candidate discovery and approval workflow for Phase 2

Routes:
- POST /jobs/{job_id}/hunting/start — Start a new hunting session
- GET /jobs/{job_id}/hunting — Render hunting detail page
- GET /jobs/{job_id}/hunting/companies — Return company cards (HTMX poll)
- GET /jobs/{job_id}/hunting/candidates — Return candidate cards (HTMX poll)
- POST /hunting/{session_id}/candidates/{candidate_id}/approve — Approve candidate
- POST /hunting/{session_id}/candidates/{candidate_id}/reject — Reject candidate
- POST /hunting/{session_id}/companies/{company_id}/remove — Remove company
"""

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlmodel import Session, select
from datetime import datetime
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from ..db import get_session
from ..models import (
    Job, HuntingSession, TargetCompany, Candidate,
    HuntingStatus, CandidateStatus
)
from ..agents.company_mapper import CompanyMapperAgent, CompanyMapperRequest
from ..agents.role_identifier import RoleIdentifierAgent, RoleIdentifierRequest

router = APIRouter(prefix="/jobs", tags=["hunting"])

# Template setup
templates_dir = Path(__file__).parent.parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))
templates.env.cache = None


# ===== Helper Functions =====

def get_latest_hunting_session(job_id: int, session: Session) -> HuntingSession | None:
    """Get the most recent HuntingSession for a job"""
    return session.exec(
        select(HuntingSession)
        .where(HuntingSession.job_id == job_id)
        .order_by(HuntingSession.created_at.desc())
    ).first()


async def run_company_mapper(job_id: int, session: Session, background_tasks: BackgroundTasks):
    """Queue CompanyMapperAgent to run in background"""
    from ..routes.jobs import get_session as job_get_session

    def _map_companies():
        # Create a fresh session for the background task
        with Session(session.get_bind()) as bg_session:
            job = bg_session.exec(select(Job).where(Job.id == job_id)).first()
            if not job:
                return

            hunting_session = get_latest_hunting_session(job_id, bg_session)
            if not hunting_session:
                return

            # Update session status
            hunting_session.status = HuntingStatus.in_progress
            hunting_session.started_at = datetime.utcnow()
            bg_session.add(hunting_session)
            bg_session.commit()

            try:
                # Run CompanyMapperAgent
                agent = CompanyMapperAgent()
                request = CompanyMapperRequest(
                    job_title=job.title,
                    job_description=job.description,
                    target_industries=job.target_industries or [],
                    target_company_types=job.target_company_types or [],
                )

                import asyncio
                response = asyncio.run(agent.run(request))

                if response.status == "success":
                    # Create TargetCompany records
                    for company in response.data.companies:
                        target_company = TargetCompany(
                            hunting_session_id=hunting_session.id,
                            name=company.name,
                            industry=company.industry,
                            size_description=company.size_description,
                            linkedin_url=company.linkedin_url,
                        )
                        bg_session.add(target_company)

                    bg_session.commit()

                    # Update session status
                    hunting_session.status = HuntingStatus.completed
                    hunting_session.completed_at = datetime.utcnow()
                    bg_session.add(hunting_session)
                    bg_session.commit()
            except Exception as e:
                hunting_session.status = HuntingStatus.failed
                bg_session.add(hunting_session)
                bg_session.commit()
                print(f"CompanyMapperAgent error: {e}")

    background_tasks.add_task(_map_companies)


async def run_role_identifier(hunting_session_id: int, session: Session, background_tasks: BackgroundTasks):
    """Queue RoleIdentifierAgent for each TargetCompany"""

    def _identify_candidates():
        with Session(session.get_bind()) as bg_session:
            hunting_session = bg_session.exec(
                select(HuntingSession).where(HuntingSession.id == hunting_session_id)
            ).first()
            if not hunting_session:
                return

            job = bg_session.exec(select(Job).where(Job.id == hunting_session.job_id)).first()
            if not job:
                return

            # Get all target companies for this session
            companies = bg_session.exec(
                select(TargetCompany).where(TargetCompany.hunting_session_id == hunting_session_id)
            ).all()

            for company in companies:
                try:
                    agent = RoleIdentifierAgent()
                    request = RoleIdentifierRequest(
                        job_title=job.title,
                        job_description=job.description,
                        seniority=job.seniority,
                        target_companies=[
                            {
                                "name": company.name,
                                "industry": company.industry,
                                "size_description": company.size_description,
                            }
                        ],
                    )

                    import asyncio
                    response = asyncio.run(agent.run(request))

                    if response.status == "success":
                        for candidate_item in response.data.candidates:
                            candidate = Candidate(
                                hunting_session_id=hunting_session_id,
                                target_company_id=company.id,
                                name=candidate_item.name,
                                current_title=candidate_item.current_title,
                                current_company=candidate_item.current_company,
                                email=candidate_item.email,
                                linkedin_url=candidate_item.linkedin_url,
                                status=CandidateStatus.hunting,
                            )
                            bg_session.add(candidate)
                        bg_session.commit()
                except Exception as e:
                    print(f"RoleIdentifierAgent error for {company.name}: {e}")

    background_tasks.add_task(_identify_candidates)


# ===== Hunting Routes =====

@router.post("/{job_id}/hunting/start", response_class=RedirectResponse)
async def start_hunting(
    job_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Start a new hunting session for a job

    Creates HuntingSession record and queues CompanyMapperAgent via BackgroundTasks.
    Redirects to hunting detail page (/jobs/{job_id}/hunting).
    """
    # Verify job exists
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Create new hunting session
    hunting_session = HuntingSession(
        job_id=job_id,
        status=HuntingStatus.pending,
    )
    session.add(hunting_session)
    session.commit()
    session.refresh(hunting_session)

    # Queue CompanyMapperAgent to run in background
    await run_company_mapper(job_id, session, background_tasks)

    # Queue RoleIdentifierAgent after companies are created
    await run_role_identifier(hunting_session.id, session, background_tasks)

    # Redirect to hunting detail page
    return RedirectResponse(url=f"/jobs/{job_id}/hunting", status_code=303)


@router.get("/{job_id}/hunting", response_class=HTMLResponse)
def get_hunting_detail(
    job_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    """Render hunting detail page with companies and candidates"""
    # Verify job exists
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get latest hunting session
    hunting_session = get_latest_hunting_session(job_id, session)

    # Get companies and candidates for this session
    companies = []
    candidates = []
    if hunting_session:
        companies = session.exec(
            select(TargetCompany)
            .where(TargetCompany.hunting_session_id == hunting_session.id)
            .order_by(TargetCompany.created_at.desc())
        ).all()

        candidates = session.exec(
            select(Candidate)
            .where(Candidate.hunting_session_id == hunting_session.id)
            .order_by(Candidate.created_at.desc())
        ).all()

    return templates.TemplateResponse(request, "jobs/hunting.html", {
        "job": job,
        "hunting_session": hunting_session,
        "companies": companies,
        "candidates": candidates,
    })


@router.get("/{job_id}/hunting/companies", response_class=HTMLResponse)
def get_hunting_companies(
    job_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    """Return HTML fragment of company cards for HTMX polling"""
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    hunting_session = get_latest_hunting_session(job_id, session)
    companies = []
    if hunting_session:
        companies = session.exec(
            select(TargetCompany)
            .where(TargetCompany.hunting_session_id == hunting_session.id)
            .order_by(TargetCompany.created_at.desc())
        ).all()

    return templates.TemplateResponse(request, "jobs/hunting-companies-fragment.html", {
        "companies": companies,
        "hunting_session": hunting_session,
    })


@router.get("/{job_id}/hunting/candidates", response_class=HTMLResponse)
def get_hunting_candidates(
    job_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    """Return HTML fragment of candidate cards for HTMX polling"""
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    hunting_session = get_latest_hunting_session(job_id, session)
    candidates = []
    if hunting_session:
        candidates = session.exec(
            select(Candidate)
            .where(Candidate.hunting_session_id == hunting_session.id)
            .order_by(Candidate.created_at.desc())
        ).all()

    return templates.TemplateResponse(request, "jobs/hunting-candidates-fragment.html", {
        "candidates": candidates,
        "hunting_session": hunting_session,
    })


@router.post("/{session_id}/candidates/{candidate_id}/approve")
def approve_candidate(
    session_id: int,
    candidate_id: int,
    session: Session = Depends(get_session),
):
    """Approve a candidate — update status to 'approved'

    Returns empty response for HTMX to handle DOM updates.
    """
    candidate = session.exec(select(Candidate).where(Candidate.id == candidate_id)).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate.status = CandidateStatus.approved
    candidate.updated_at = datetime.utcnow()
    session.add(candidate)
    session.commit()

    return ""


@router.post("/{session_id}/candidates/{candidate_id}/reject")
def reject_candidate(
    session_id: int,
    candidate_id: int,
    session: Session = Depends(get_session),
):
    """Reject a candidate — update status to 'rejected'

    Returns empty response for HTMX to handle DOM updates.
    """
    candidate = session.exec(select(Candidate).where(Candidate.id == candidate_id)).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate.status = CandidateStatus.rejected
    candidate.updated_at = datetime.utcnow()
    session.add(candidate)
    session.commit()

    return ""


@router.post("/{session_id}/companies/{company_id}/remove")
def remove_company(
    session_id: int,
    company_id: int,
    session: Session = Depends(get_session),
):
    """Remove a target company — delete TargetCompany record

    Returns empty response for HTMX to remove the element from DOM.
    """
    company = session.exec(select(TargetCompany).where(TargetCompany.id == company_id)).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    session.delete(company)
    session.commit()

    return ""
