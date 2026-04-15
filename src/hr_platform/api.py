from __future__ import annotations

"""
HR Platform — FastAPI REST layer
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .db.database import (
    get_candidate,
    get_client,
    get_evaluations_for_job,
    get_job,
    list_jobs,
    save_client,
    search_candidates,
)
from .models.schema import Client, Job
from .orchestrator import (
    WorkflowResult,
    run_full_workflow,
    step_ingest_cv,
    step_ingest_linkedin,
    HRWorkflowContext,
)

app = FastAPI(
    title="HR Intelligence Platform",
    description="AI-powered hiring pipeline API",
    version="0.1.0",
)

# Serve the frontend UI
_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index():
    return (_STATIC_DIR / "index.html").read_text()

@app.get("/health")
def health():
    return {"status": "ok"}


# ─── Clients ──────────────────────────────────────────────────────────────────

@app.post("/clients", response_model=Client, status_code=201)
def create_client(client: Client):
    save_client(client)
    return client


@app.get("/clients/{client_id}", response_model=Client)
def read_client(client_id: str):
    c = get_client(client_id)
    if not c:
        raise HTTPException(404, "Client not found")
    return c


# ─── Jobs ─────────────────────────────────────────────────────────────────────

@app.post("/jobs", response_model=Job, status_code=201)
def create_job(job: Job):
    from .db.database import save_job
    save_job(job)
    return job


@app.get("/jobs/{job_id}", response_model=Job)
def read_job(job_id: str):
    j = get_job(job_id)
    if not j:
        raise HTTPException(404, "Job not found")
    return j


@app.get("/clients/{client_id}/jobs", response_model=list[Job])
def list_client_jobs(client_id: str):
    return list_jobs(client_id)


# ─── Candidates ───────────────────────────────────────────────────────────────

@app.get("/candidates/{candidate_id}")
def read_candidate(candidate_id: str):
    c = get_candidate(candidate_id)
    if not c:
        raise HTTPException(404, "Candidate not found")
    return c


@app.get("/clients/{client_id}/candidates")
def search(
    client_id: str,
    skill: str | None = None,
    min_experience: float | None = None,
    industry: str | None = None,
    reusable_only: bool = False,
):
    return search_candidates(client_id, skill, min_experience, industry, reusable_only)


@app.post("/candidates/ingest/cv", status_code=201)
async def ingest_cv(
    client_id: Annotated[str, Form()],
    job_id: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
):
    """Upload a CV PDF and ingest it as a candidate."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    suffix = Path(file.filename or "cv.pdf").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        ctx = HRWorkflowContext(job=job)
        candidate = step_ingest_cv(tmp_path, client_id, ctx)
    finally:
        os.unlink(tmp_path)

    return {"candidate_id": candidate.candidate_id, "name": candidate.name}


class LinkedInIngestRequest(BaseModel):
    client_id: str
    job_id: str
    profile_text: str


@app.post("/candidates/ingest/linkedin", status_code=201)
def ingest_linkedin(req: LinkedInIngestRequest):
    """Ingest a pasted LinkedIn profile (no scraping)."""
    job = get_job(req.job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    ctx = HRWorkflowContext(job=job)
    candidate = step_ingest_linkedin(req.profile_text, req.client_id, ctx)
    return {"candidate_id": candidate.candidate_id, "name": candidate.name}


# ─── Evaluations ──────────────────────────────────────────────────────────────

@app.get("/jobs/{job_id}/evaluations")
def get_job_evaluations(job_id: str):
    return get_evaluations_for_job(job_id)


# ─── Full workflow ─────────────────────────────────────────────────────────────

class WorkflowRequest(BaseModel):
    job_id: str
    client_name: str = "Client"
    linkedin_profiles: list[str] = []
    transcripts: dict[str, str] = {}  # candidate_id → transcript
    output_dir: str = "/tmp"


class WorkflowResponse(BaseModel):
    candidates_processed: int
    candidates_screened: int
    report_path: str | None
    errors: list[str]
    kpi_id: str


@app.post("/workflow/run", response_model=WorkflowResponse)
def run_workflow(req: WorkflowRequest):
    """
    Run the full HR pipeline for a job with optional LinkedIn profiles and transcripts.
    CV files should be ingested separately via /candidates/ingest/cv first.
    """
    job = get_job(req.job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    result: WorkflowResult = run_full_workflow(
        job=job,
        linkedin_profiles=req.linkedin_profiles,
        transcripts=req.transcripts,
        client_name=req.client_name,
        output_dir=req.output_dir,
    )

    return WorkflowResponse(
        candidates_processed=result.kpi.candidates_processed,
        candidates_screened=result.kpi.candidates_screened,
        report_path=result.report_path,
        errors=result.errors,
        kpi_id=result.kpi.kpi_id,
    )


@app.get("/workflow/report/{job_id}")
def download_report(job_id: str):
    """Download the generated .pptx report for a job."""
    # Find latest report for this job in the default output dir
    output_dir = Path("/tmp")
    matches = sorted(output_dir.glob(f"*{job_id}*.pptx"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        raise HTTPException(404, "No report found for this job")
    return FileResponse(
        str(matches[0]),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=matches[0].name,
    )
