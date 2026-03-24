from fastapi import APIRouter, Depends, HTTPException, Request, Form
from sqlmodel import Session, select
from datetime import datetime
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json

from ..db import get_session
from ..models import Job, Client, JobStatus
from ..schemas import JobCreate, JobUpdate, JobRead, JobListItem

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Template setup
templates_dir = Path(__file__).parent.parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))
templates.env.cache = None  # disable LRU cache — workaround for Jinja2 3.1.6 / Python 3.14 hashability bug


# ===== HTML View Routes (GET) =====

@router.get("/", response_class=HTMLResponse)
def jobs_list_view(
    request: Request,
    session: Session = Depends(get_session),
):
    """Render job list dashboard (JOB-03)"""
    jobs = session.exec(
        select(Job)
        .where(Job.status != JobStatus.closed)
        .order_by(Job.created_at.desc())
    ).all()

    # Deserialize JSON columns in case SQLAlchemy returns strings
    for job in jobs:
        if isinstance(job.target_industries, str):
            job.target_industries = json.loads(job.target_industries) if job.target_industries else []
        if isinstance(job.target_company_types, str):
            job.target_company_types = json.loads(job.target_company_types) if job.target_company_types else []

    return templates.TemplateResponse(request, "jobs/list.html", {"jobs": jobs})


@router.get("/create", response_class=HTMLResponse)
def job_create_form(
    request: Request,
    session: Session = Depends(get_session),
):
    """Render job creation form"""
    clients = session.exec(select(Client)).all()
    return templates.TemplateResponse(request, "jobs/form.html", {
        "clients": clients,
        "job": None,
        "errors": {},
    })


@router.get("/{job_id}/edit", response_class=HTMLResponse)
def job_edit_form(
    job_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    """Render job edit form"""
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    clients = session.exec(select(Client)).all()

    # Deserialize JSON columns
    if isinstance(job.target_industries, str):
        job.target_industries = json.loads(job.target_industries) if job.target_industries else []
    if isinstance(job.target_company_types, str):
        job.target_company_types = json.loads(job.target_company_types) if job.target_company_types else []

    return templates.TemplateResponse(request, "jobs/form.html", {
        "clients": clients,
        "job": job,
        "errors": {},
    })


@router.get("/{job_id}", response_class=HTMLResponse)
def job_detail_view(
    job_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    """Render job detail page"""
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    client = session.exec(select(Client).where(Client.id == job.client_id)).first()

    # Deserialize JSON columns in case SQLAlchemy returns strings
    if isinstance(job.target_industries, str):
        job.target_industries = json.loads(job.target_industries) if job.target_industries else []
    if isinstance(job.target_company_types, str):
        job.target_company_types = json.loads(job.target_company_types) if job.target_company_types else []

    return templates.TemplateResponse(request, "jobs/detail.html", {
        "job": job,
        "client": client,
    })


# ===== Form Submission Routes (POST from HTML forms) =====

@router.post("/", response_class=RedirectResponse)
def create_job_form(
    request: Request,
    client_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    seniority: str = Form(...),
    salary_min: int | None = Form(None),
    salary_max: int | None = Form(None),
    required_experience_years: int | None = Form(None),
    target_industries: str = Form(""),
    target_company_types: str = Form(""),
    session: Session = Depends(get_session),
):
    """Create job from HTML form submission (JOB-01)

    Handles comma-separated strings and converts to JSON arrays.
    Redirects to job detail on success.
    """
    try:
        # Verify client exists
        client = session.exec(select(Client).where(Client.id == client_id)).first()
        if not client:
            raise ValueError("Client not found")

        # Parse comma-separated strings into lists (form inputs send strings)
        industries = [i.strip() for i in target_industries.split(',') if i.strip()] if target_industries else []
        company_types = [c.strip() for c in target_company_types.split(',') if c.strip()] if target_company_types else []

        # Create job
        db_job = Job(
            client_id=client_id,
            title=title,
            description=description,
            seniority=seniority,
            salary_min=salary_min,
            salary_max=salary_max,
            required_experience_years=required_experience_years,
            target_industries=industries,
            target_company_types=company_types,
            status=JobStatus.hunting,
        )
        session.add(db_job)
        session.commit()
        session.refresh(db_job)

        # Redirect to job detail
        return RedirectResponse(url=f"/jobs/{db_job.id}", status_code=303)

    except Exception as e:
        # On error, redirect back to form with error message
        return RedirectResponse(url="/jobs/create", status_code=303)


@router.post("/{job_id}/edit", response_class=RedirectResponse)
def update_job_form(
    job_id: int,
    request: Request,
    client_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    seniority: str = Form(...),
    salary_min: int | None = Form(None),
    salary_max: int | None = Form(None),
    required_experience_years: int | None = Form(None),
    target_industries: str = Form(""),
    target_company_types: str = Form(""),
    session: Session = Depends(get_session),
):
    """Update job from HTML form submission"""
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    industries = [i.strip() for i in target_industries.split(',') if i.strip()] if target_industries else []
    company_types = [c.strip() for c in target_company_types.split(',') if c.strip()] if target_company_types else []

    job.client_id = client_id
    job.title = title
    job.description = description
    job.seniority = seniority
    job.salary_min = salary_min
    job.salary_max = salary_max
    job.required_experience_years = required_experience_years
    job.target_industries = industries
    job.target_company_types = company_types
    job.updated_at = datetime.utcnow()

    session.add(job)
    session.commit()
    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


# ===== API Routes (JSON-based) =====

@router.post("/api", response_model=JobRead, status_code=201)
def create_job_api(
    job_in: JobCreate,
    session: Session = Depends(get_session),
):
    """Create job via JSON API (for programmatic access)"""
    # Verify client exists
    client = session.exec(select(Client).where(Client.id == job_in.client_id)).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    db_job = Job(
        client_id=job_in.client_id,
        title=job_in.title,
        description=job_in.description,
        seniority=job_in.seniority,
        salary_min=job_in.salary_min,
        salary_max=job_in.salary_max,
        required_experience_years=job_in.required_experience_years,
        target_industries=job_in.target_industries,
        target_company_types=job_in.target_company_types,
        status=JobStatus.hunting,
    )
    session.add(db_job)
    session.commit()
    session.refresh(db_job)
    return db_job


@router.get("/api/jobs", response_model=list[JobListItem])
def list_jobs_api(
    session: Session = Depends(get_session),
):
    """List all active jobs via API (JSON)

    Returns jobs with status != 'closed'. Ordered by created_at descending.
    """
    jobs = session.exec(
        select(Job)
        .where(Job.status != JobStatus.closed)
        .order_by(Job.created_at.desc())
    ).all()
    return jobs


@router.get("/api/{job_id}", response_model=JobRead)
def get_job_api(
    job_id: int,
    session: Session = Depends(get_session),
):
    """Get job detail via API (JSON)"""
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.put("/api/{job_id}", response_model=JobRead)
def update_job_api(
    job_id: int,
    job_in: JobUpdate,
    session: Session = Depends(get_session),
):
    """Update an existing job via API (JSON)"""
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Update only provided fields
    update_data = job_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)

    job.updated_at = datetime.utcnow()
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


# ===== Archive Route (HTMX response) =====

@router.post("/{job_id}/archive")
def archive_job(
    job_id: int,
    session: Session = Depends(get_session),
):
    """Archive a job — set status to 'closed' (JOB-04)

    Returns empty response (HTMX removes the element from DOM).
    """
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = JobStatus.closed
    job.updated_at = datetime.utcnow()
    session.add(job)
    session.commit()
    session.refresh(job)

    # Return empty response for HTMX to remove the element
    return ""


@router.post("/{job_id}/status")
def update_job_status(
    job_id: int,
    status: JobStatus,
    session: Session = Depends(get_session),
):
    """Update job status (for JOB-03 pipeline state changes)"""
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = status
    job.updated_at = datetime.utcnow()
    session.add(job)
    session.commit()
    session.refresh(job)

    return {"message": f"Job status updated to {status}", "id": job.id, "status": job.status}
