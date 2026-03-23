---
phase: 01-foundation-job-project-setup
plan: 02
type: execute
wave: 2
depends_on: [01]
files_modified:
  - src/app/routes/__init__.py
  - src/app/routes/jobs.py
  - src/app/routes/clients.py
  - src/app/main.py
  - templates/base.html
  - templates/jobs/list.html
  - templates/jobs/form.html
  - templates/jobs/detail.html
  - templates/clients/create.html
  - static/style.css
  - src/app/schemas.py
autonomous: true
requirements: [JOB-01, JOB-02, JOB-03, JOB-04]
user_setup: []

must_haves:
  truths:
    - "Consultant can create a job via web form (POST /jobs) with all JOB-01 fields"
    - "Consultant can view all active jobs on a dashboard with status badges"
    - "Consultant can see job details with edit and archive actions"
    - "Consultant can archive a job (removes from active list)"
    - "Consultant can create a minimal client before creating a job"
    - "Forms validate required fields server-side and show errors"
    - "UI uses Tailwind CSS and HTMX for partial updates"
  artifacts:
    - path: "src/app/routes/jobs.py"
      provides: "Job CRUD routes (create, list, detail, update, archive)"
      exports: ["router"]
      min_lines: 80
    - path: "src/app/routes/clients.py"
      provides: "Minimal client creation route"
      exports: ["router"]
      min_lines: 30
    - path: "templates/base.html"
      provides: "Base template with Tailwind CDN, HTMX, responsive layout"
      must_contain: ["<!DOCTYPE html>", "tailwindcss", "htmx"]
    - path: "templates/jobs/list.html"
      provides: "Dashboard with job cards, status badges, empty state"
      must_contain: ["job card", "status badge", "Create Job"]
    - path: "templates/jobs/form.html"
      provides: "Create/edit job form with validation errors"
      must_contain: ["input", "textarea", "select", "Save Job"]
    - path: "src/app/schemas.py"
      provides: "Pydantic request/response schemas for FastAPI validation"
      exports: ["JobCreate", "JobUpdate", "JobRead"]
      min_lines: 30
  key_links:
    - from: "src/app/main.py"
      to: "src/app/routes/jobs.py"
      via: "include_router(jobs_router)"
      pattern: "include_router"
    - from: "templates/jobs/list.html"
      to: "src/app/routes/jobs.py"
      via: "HTMX POST to /jobs/archive"
      pattern: "hx-post.*archive"
    - from: "templates/jobs/form.html"
      to: "src/app/routes/jobs.py"
      via: "POST /jobs to create job"
      pattern: "hx-post.*jobs"
    - from: "templates/jobs/list.html"
      to: "templates/jobs/detail.html"
      via: "job card click links to detail view"
      pattern: "/jobs/\\{id\\}"
    - from: "templates/jobs/form.html"
      to: "src/app/routes/clients.py"
      via: "Link to /clients/create for first-time client creation"
      pattern: "/clients/create"
---

<objective>
Implement Phase 1 API routes and Jinja2/HTMX user interface for job management. Routes handle JOB-01 (create job), JOB-03 (dashboard), and JOB-04 (archive). UI uses Tailwind CSS via CDN with HTMX for partial page updates.

Purpose: Bring data models from Plan 01 to life with a working consultant interface. Complete Phase 1 scope: create jobs, define search scope (target industries/types), view dashboard with status, archive jobs.

Output: Fully functional Phase 1 feature set with job creation form, dashboard, job detail view, and archive action. UI passes 01-UI-SPEC.md requirements.
</objective>

<execution_context>
@/Users/juanjavierdonoso/.claude/get-shit-done/workflows/execute-plan.md
@/Users/juanjavierdonoso/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-foundation-job-project-setup/01-CONTEXT.md
@.planning/phases/01-foundation-job-project-setup/01-UI-SPEC.md
@.planning/phases/01-foundation-job-project-setup/01-RESEARCH.md

From 01-UI-SPEC.md (Tailwind design system and interaction patterns):
- Tailwind CSS via CDN (no build step)
- Spacing: xs=4px, sm=8px, md=16px, lg=24px, xl=32px, 2xl=48px, 3xl=64px
- Typography: body 16px/400, label 14px/500, heading 24px/600, display 32px/700
- Colors: white bg, #F3F4F6 secondary, #2563EB accent, #DC2626 destructive
- Card layout with 24px gap, 1px border #E5E7EB, shadow on hover
- Status badges: Hunting=info blue, Shortlisting=warning orange, Interviewing=warning orange, Closed=gray
- Buttons: primary blue, secondary gray, destructive red
- Form validation: errors shown below field in red
- HTMX: POST /jobs/archive with confirmation modal

Locked Decisions from 01-CONTEXT.md:
- Jinja2 templates with FastAPI
- HTMX for partial updates
- Client as separate table (FK on Job)
- JSON columns for target_industries, target_company_types (no separate tags table)

APIs to Implement:
JOB-01:
- POST /jobs — create job with title, description, seniority, salary_min/max, required_experience_years, client_id, target_industries, target_company_types
- GET /jobs/{id} — view job detail

JOB-03:
- GET /jobs — list all active jobs with status

JOB-04:
- POST /jobs/{id}/archive — archive a job

Client (minimal):
- POST /clients — create client (name only)
- GET /clients — list clients (for dropdown in job form)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create Pydantic request/response schemas for FastAPI validation</name>
  <files>
    src/app/schemas.py
  </files>
  <read_first>
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/models.py (Job and Client models)
  </read_first>
  <action>
Create src/app/schemas.py with request/response schemas for FastAPI routes:

```python
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from .models import JobStatus

# Client schemas
class ClientCreate(BaseModel):
    """Request schema for creating a client"""
    name: str = Field(..., min_length=1, max_length=200)

class ClientRead(BaseModel):
    """Response schema for client"""
    id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True  # Allow Pydantic to read from SQLModel instances

# Job schemas
class JobCreate(BaseModel):
    """Request schema for creating a new job"""
    client_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=10)
    seniority: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    required_experience_years: Optional[int] = None
    target_industries: List[str] = Field(default=[])
    target_company_types: List[str] = Field(default=[])

class JobUpdate(BaseModel):
    """Request schema for updating a job"""
    title: Optional[str] = None
    description: Optional[str] = None
    seniority: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    required_experience_years: Optional[int] = None
    target_industries: Optional[List[str]] = None
    target_company_types: Optional[List[str]] = None

class JobRead(BaseModel):
    """Response schema for job detail"""
    id: int
    client_id: int
    title: str
    description: str
    seniority: str
    salary_min: Optional[int]
    salary_max: Optional[int]
    required_experience_years: Optional[int]
    target_industries: List[str]
    target_company_types: List[str]
    status: JobStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class JobListItem(BaseModel):
    """Response schema for job in list (includes related client data)"""
    id: int
    title: str
    client_id: int
    status: JobStatus
    created_at: datetime
```

Notes:
- BaseModel from pydantic (not SQLModel) for request/response schemas
- from_attributes=True allows reading from SQLModel table instances
- Field validators with min/max length for required text fields
- Optional types for nullable fields
- JobListItem used for dashboard list (lighter payload)
- JobRead used for detail view (full data)
  </action>
  <verify>
    <automated>
      # Check schemas.py has request schemas
      grep -q "class ClientCreate" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/schemas.py && \
      grep -q "class JobCreate" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/schemas.py && \
      # Check response schemas
      grep -q "class JobRead" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/schemas.py && \
      grep -q "class ClientRead" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/schemas.py && \
      # Check from_attributes
      grep -q "from_attributes = True" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/schemas.py && \
      echo "PASS" || echo "FAIL"
    </automated>
  </verify>
  <done>
    - src/app/schemas.py created with ClientCreate, ClientRead schemas
    - JobCreate, JobUpdate, JobRead schemas for full job CRUD
    - JobListItem for dashboard list view
    - All schemas use Pydantic validation (min_length, max_length, etc.)
    - from_attributes=True enables reading from SQLModel table instances
  </done>
</task>

<task type="auto">
  <name>Task 2: Create client routes (minimal create and list for job form dropdown)</name>
  <files>
    src/app/routes/__init__.py
    src/app/routes/clients.py
  </files>
  <read_first>
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/models.py (Client model)
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/schemas.py (ClientCreate, ClientRead)
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/db.py (get_session dependency)
  </read_first>
  <action>
1. Create src/app/routes/__init__.py (empty file to make routes a package):
   ```python
   """FastAPI route modules"""
   ```

2. Create src/app/routes/clients.py with minimal client CRUD for Phase 1:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..db import get_session
from ..models import Client
from ..schemas import ClientCreate, ClientRead
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from fastapi import Request

router = APIRouter(prefix="/clients", tags=["clients"])

# Template setup
templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

@router.post("/", response_model=ClientRead)
def create_client(
    client_in: ClientCreate,
    session: Session = Depends(get_session),
):
    """Create a new client (Phase 1: minimal client creation for job FK)"""
    db_client = Client(name=client_in.name)
    session.add(db_client)
    session.commit()
    session.refresh(db_client)
    return db_client

@router.get("/", response_model=list[ClientRead])
def list_clients(
    session: Session = Depends(get_session),
):
    """List all clients for dropdown in job form"""
    clients = session.exec(select(Client)).all()
    return clients

@router.get("/{client_id}", response_model=ClientRead)
def get_client(
    client_id: int,
    session: Session = Depends(get_session),
):
    """Get a specific client by ID"""
    client = session.exec(select(Client).where(Client.id == client_id)).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@router.get("/create", response_class=HTMLResponse)
def client_create_form(
    request: Request,
    session: Session = Depends(get_session),
):
    """Render client creation form"""
    return templates.TemplateResponse("clients/create.html", {
        "request": request,
        "errors": {},
    })

```

Notes:
- Minimal scope: create (POST) and list (GET) only — no edit/delete in Phase 1
- List endpoint used for job form client dropdown
- HTTPException 404 if client not found
- SessionMaker dependency injected by FastAPI
  </action>
  <verify>
    <automated>
      # Check routes/__init__.py exists
      test -f /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/routes/__init__.py && \
      # Check routes/clients.py has routes
      grep -q "def create_client" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/routes/clients.py && \
      grep -q "def list_clients" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/routes/clients.py && \
      # Check router is exported
      grep -q "router = APIRouter" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/routes/clients.py && \
      echo "PASS" || echo "FAIL"
    </automated>
  </verify>
  <done>
    - src/app/routes/__init__.py created
    - src/app/routes/clients.py created with POST /clients (create)
    - GET /clients endpoint for dropdown list
    - GET /clients/{id} for detail
    - APIRouter exported as `router`
  </done>
</task>

<task type="auto">
  <name>Task 3: Create job routes (CRUD for JOB-01, JOB-03, JOB-04)</name>
  <files>
    src/app/routes/jobs.py
  </files>
  <read_first>
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/models.py (Job, JobStatus)
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/schemas.py (JobCreate, JobRead)
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/db.py (get_session)
  </read_first>
  <action>
Create src/app/routes/jobs.py with all job management routes (JOB-01, JOB-03, JOB-04):

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from datetime import datetime

from ..db import get_session
from ..models import Job, Client, JobStatus
from ..schemas import JobCreate, JobUpdate, JobRead, JobListItem

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.post("/", response_model=JobRead, status_code=201)
def create_job(
    job_in: JobCreate,
    session: Session = Depends(get_session),
):
    """Create a new job (JOB-01)

    Required fields: title, description, seniority, client_id
    Optional fields: salary_min, salary_max, required_experience_years, target_industries, target_company_types
    """
    # Verify client exists
    client = session.exec(select(Client).where(Client.id == job_in.client_id)).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Create job with status=hunting (default from model)
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

@router.get("/", response_model=list[JobListItem])
def list_jobs(
    session: Session = Depends(get_session),
):
    """List all active jobs (JOB-03 dashboard)

    Returns jobs with status != 'closed'. Ordered by created_at descending.
    """
    jobs = session.exec(
        select(Job)
        .where(Job.status != JobStatus.closed)
        .order_by(Job.created_at.desc())
    ).all()
    return jobs

@router.get("/{job_id}", response_model=JobRead)
def get_job(
    job_id: int,
    session: Session = Depends(get_session),
):
    """Get job detail (JOB-01 view)"""
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.put("/{job_id}", response_model=JobRead)
def update_job(
    job_id: int,
    job_in: JobUpdate,
    session: Session = Depends(get_session),
):
    """Update an existing job"""
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

@router.post("/{job_id}/archive")
def archive_job(
    job_id: int,
    session: Session = Depends(get_session),
):
    """Archive a job — set status to 'closed' (JOB-04)"""
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = JobStatus.closed
    job.updated_at = datetime.utcnow()
    session.add(job)
    session.commit()
    session.refresh(job)

    return {"message": "Job archived", "id": job.id, "status": job.status}

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
```

Key implementation details:
- POST /jobs validates client_id exists before creating
- GET /jobs returns only non-closed jobs (active jobs for dashboard)
- POST /jobs/{id}/archive sets status to 'closed' (soft delete pattern)
- PUT /jobs/{id} for full job edit
- POST /jobs/{id}/status for status transitions
- All routes use SQLModel session dependency
- HTMX will call these endpoints via form submission
  </action>
  <verify>
    <automated>
      # Check routes exist
      grep -q "def create_job" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/routes/jobs.py && \
      grep -q "def list_jobs" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/routes/jobs.py && \
      grep -q "def get_job" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/routes/jobs.py && \
      grep -q "def archive_job" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/routes/jobs.py && \
      # Check status field update
      grep -q "JobStatus.closed" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/routes/jobs.py && \
      # Check router export
      grep -q "router = APIRouter" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/routes/jobs.py && \
      echo "PASS" || echo "FAIL"
    </automated>
  </verify>
  <done>
    - src/app/routes/jobs.py created with all CRUD routes
    - POST /jobs creates job (JOB-01)
    - GET /jobs lists active jobs (JOB-03)
    - GET /jobs/{id} gets job detail
    - PUT /jobs/{id} updates job
    - POST /jobs/{id}/archive archives job (JOB-04)
    - POST /jobs/{id}/status changes status
    - APIRouter exported as `router`
  </done>
</task>

<task type="auto">
  <name>Task 4: Wire routes into main FastAPI app</name>
  <files>
    src/app/main.py
  </files>
  <read_first>
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/main.py (current app structure)
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/routes/jobs.py (router object)
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/routes/clients.py (router object)
  </read_first>
  <action>
Update src/app/main.py to include route routers:

Add these imports at the top:
```python
from fastapi.middleware.cors import CORSMiddleware
from .routes import jobs, clients
```

After `app = FastAPI(...)` line, add route registration:
```python
# Include API routers
app.include_router(jobs.router)
app.include_router(clients.router)

# Add CORS middleware (for later frontend integration if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

This wires the /jobs and /clients routes into the main FastAPI app.
  </action>
  <verify>
    <automated>
      # Check routers are imported
      grep -q "from .routes import" /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/main.py && \
      # Check routers are included
      grep -q "include_router.*jobs" /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/main.py && \
      grep -q "include_router.*clients" /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/main.py && \
      echo "PASS" || echo "FAIL"
    </automated>
  </verify>
  <done>
    - src/app/main.py updated to import routes modules
    - include_router(jobs.router) adds /jobs routes
    - include_router(clients.router) adds /clients routes
    - CORS middleware added for cross-origin requests
    - App now has full API: POST/GET /jobs, POST/GET /clients, POST /jobs/{id}/archive
  </done>
</task>

<task type="auto">
  <name>Task 5: Create Jinja2 base template with Tailwind CDN and HTMX</name>
  <files>
    templates/base.html
  </files>
  <read_first>
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/.planning/phases/01-foundation-job-project-setup/01-UI-SPEC.md (lines 16-50 for design system)
  </read_first>
  <action>
Create templates/base.html as Jinja2 base template with Tailwind CDN and HTMX:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}HR Recruitment AI{% endblock %}</title>

    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>

    <!-- HTMX CDN -->
    <script src="https://unpkg.com/htmx.org@2.0.8"></script>

    <!-- Heroicons SVG CDN (for icons if needed) -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/heroicons@2/outline/index.min.css">

    <!-- Custom Tailwind config for semantic colors -->
    <style>
        :root {
            --color-accent: #2563EB;
            --color-secondary: #F3F4F6;
            --color-destructive: #DC2626;
        }

        /* Status badge colors per 01-UI-SPEC.md */
        .badge-hunting {
            @apply bg-blue-100 text-blue-900;
        }
        .badge-shortlisting {
            @apply bg-amber-100 text-amber-900;
        }
        .badge-interviewing {
            @apply bg-amber-100 text-amber-900;
        }
        .badge-closed {
            @apply bg-gray-100 text-gray-900;
        }

        /* Button styles per 01-UI-SPEC.md */
        .btn-primary {
            @apply bg-blue-600 text-white px-4 py-2 rounded border-0 font-semibold hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed;
        }
        .btn-secondary {
            @apply bg-gray-100 text-gray-900 px-4 py-2 rounded border border-gray-300 font-medium hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed;
        }
        .btn-destructive {
            @apply bg-red-600 text-white px-4 py-2 rounded border-0 font-semibold hover:bg-red-700 active:bg-red-800 disabled:opacity-50 disabled:cursor-not-allowed;
        }

        /* Form input styles per 01-UI-SPEC.md */
        .form-input {
            @apply w-full px-4 py-2 border border-gray-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-opacity-20;
        }
        .form-input:invalid {
            @apply border-red-600;
        }
        .form-error {
            @apply text-red-600 text-sm mt-1;
        }
    </style>

    {% block extra_css %}{% endblock %}
</head>
<body class="bg-white text-gray-900 font-sans leading-relaxed">
    <!-- Header/Navigation -->
    <header class="sticky top-0 bg-white border-b border-gray-200 shadow-sm">
        <nav class="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
            <h1 class="text-2xl font-bold text-blue-600">HR Recruitment AI</h1>
            <ul class="flex gap-6">
                <li><a href="/" class="text-gray-700 hover:text-blue-600">Dashboard</a></li>
                <li><a href="/docs" class="text-gray-700 hover:text-blue-600">API Docs</a></li>
            </ul>
        </nav>
    </header>

    <!-- Main content -->
    <main class="max-w-6xl mx-auto px-6 py-8">
        {% block content %}{% endblock %}
    </main>

    <!-- Footer -->
    <footer class="bg-gray-50 border-t border-gray-200 mt-16">
        <div class="max-w-6xl mx-auto px-6 py-6 text-center text-sm text-gray-600">
            <p>&copy; 2026 HR Recruitment AI. All rights reserved.</p>
        </div>
    </footer>

    {% block extra_js %}{% endblock %}
</body>
</html>
```

Notes on implementation:
- Tailwind CDN script for no-build styling
- HTMX CDN for dynamic interactions
- Custom CSS classes for badge status colors (per 01-UI-SPEC.md)
- Button styles (.btn-primary, .btn-secondary, .btn-destructive)
- Form input styles with focus ring and error states
- Responsive max-width container (6xl = 1200px per 01-UI-SPEC.md)
- Block tags for content inheritance in child templates
- Header with app title and navigation links
  </action>
  <verify>
    <automated>
      # Check base.html exists
      test -f /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/templates/base.html && \
      # Check Tailwind CDN
      grep -q "cdn.tailwindcss.com" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/templates/base.html && \
      # Check HTMX CDN
      grep -q "htmx.org" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/templates/base.html && \
      # Check block tags for inheritance
      grep -q "{% block content %}" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/templates/base.html && \
      # Check button classes defined
      grep -q "btn-primary" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/templates/base.html && \
      echo "PASS" || echo "FAIL"
    </automated>
  </verify>
  <done>
    - templates/base.html created with Tailwind CDN and HTMX
    - Header with navigation
    - Main content block for child templates
    - Custom CSS classes for buttons, badges, form inputs
    - Status badge colors: hunting (blue), shortlisting (amber), interviewing (amber), closed (gray)
    - Form styling with focus ring and error states
    - Footer
  </done>
</task>

<task type="auto">
  <name>Task 6: Create job list dashboard template (JOB-03)</name>
  <files>
    templates/jobs/list.html
  </files>
  <read_first>
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/.planning/phases/01-foundation-job-project-setup/01-UI-SPEC.md (lines 195-201 for dashboard layout)
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/templates/base.html (for template structure)
  </read_first>
  <action>
Create templates/jobs/list.html to display job dashboard (JOB-03):

```html
{% extends "base.html" %}

{% block title %}Jobs — HR Recruitment AI{% endblock %}

{% block content %}
<div class="mb-8">
    <div class="flex items-center justify-between mb-2">
        <h2 class="text-4xl font-bold">Jobs</h2>
        <a href="/jobs/create" class="btn-primary">+ Create Job</a>
    </div>
    <p class="text-gray-600">Manage your active and closed jobs</p>
</div>

{% if jobs %}
<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    {% for job in jobs %}
    <div id="job-row-{{ job.id }}" class="bg-white border border-gray-200 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow cursor-pointer" onclick="window.location.href='/jobs/{{ job.id }}'">
        <!-- Job card header with title and status -->
        <div class="flex items-start justify-between mb-4">
            <div class="flex-1">
                <h3 class="text-xl font-semibold text-gray-900">{{ job.title }}</h3>
                <p class="text-sm text-gray-600 mt-1">Client: {{ job.client_id }}</p>
            </div>
            <span class="badge-{{ job.status }} px-3 py-1 rounded text-sm font-medium">
                {{ job.status.replace('_', ' ').title() }}
            </span>
        </div>

        <!-- Job description (truncated) -->
        <p class="text-gray-700 text-sm mb-4 line-clamp-2">{{ job.description }}</p>

        <!-- Job metadata -->
        <div class="grid grid-cols-2 gap-4 mb-4 text-sm">
            <div>
                <span class="text-gray-600">Seniority:</span>
                <span class="font-medium">{{ job.seniority }}</span>
            </div>
            {% if job.salary_min or job.salary_max %}
            <div>
                <span class="text-gray-600">Salary:</span>
                <span class="font-medium">
                    {% if job.salary_min and job.salary_max %}
                        ${{ job.salary_min }}—${{ job.salary_max }}
                    {% elif job.salary_min %}
                        ${{ job.salary_min }}+
                    {% else %}
                        ${{ job.salary_max }}
                    {% endif %}
                </span>
            </div>
            {% endif %}
        </div>

        <!-- Target industries/company types -->
        {% if job.target_industries or job.target_company_types %}
        <div class="mb-4">
            {% if job.target_industries %}
            <p class="text-xs text-gray-600 mb-2">
                <strong>Industries:</strong> {{ job.target_industries|join(', ') }}
            </p>
            {% endif %}
            {% if job.target_company_types %}
            <p class="text-xs text-gray-600">
                <strong>Company Types:</strong> {{ job.target_company_types|join(', ') }}
            </p>
            {% endif %}
        </div>
        {% endif %}

        <!-- Card actions (stop click propagation) -->
        <div class="flex gap-2 mt-4 pt-4 border-t border-gray-200" onclick="event.stopPropagation()">
            <a href="/jobs/{{ job.id }}/edit" class="btn-secondary text-sm flex-1 text-center">Edit</a>
            <button hx-post="/jobs/{{ job.id }}/archive" hx-target="#job-row-{{ job.id }}" hx-swap="outerHTML" onclick="return confirm('Archive this job?')" class="btn-destructive text-sm flex-1">Archive</button>
        </div>
    </div>
    {% endfor %}
</div>
{% else %}
<!-- Empty state per 01-UI-SPEC.md -->
<div class="flex flex-col items-center justify-center py-12 text-center">
    <svg class="w-16 h-16 text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
    <h3 class="text-2xl font-semibold text-gray-900 mb-2">No jobs yet</h3>
    <p class="text-gray-600 mb-6 max-w-md">
        Start by creating your first job. Set the title, seniority, salary range, and target industries. Then click Create to save.
    </p>
    <a href="/jobs/create" class="btn-primary">Create Your First Job</a>
</div>
{% endif %}
{% endblock %}
```

Notes on implementation:
- Grid layout: 1 column on mobile, 2 columns on lg breakpoint (per 01-UI-SPEC.md)
- Card hover effect with shadow increase
- Status badge with color class (badge-{{ job.status }})
- Salary display logic (handles min/max combinations)
- Target industries/company types displayed as comma-separated (from JSON list)
- Archive button with HTMX: POST to /jobs/{id}/archive, replaces card on success
- Edit link for job detail/edit view
- Empty state with icon and CTA (per 01-UI-SPEC.md)
- onclick="event.stopPropagation()" on action buttons to prevent card click
  </action>
  <verify>
    <automated>
      # Check list.html exists
      test -f /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/templates/jobs/list.html && \
      # Check extends base
      grep -q "extends.*base" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/templates/jobs/list.html && \
      # Check for job card grid
      grep -q "grid.*grid-cols" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/templates/jobs/list.html && \
      # Check for status badge
      grep -q "badge-.*status" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/templates/jobs/list.html && \
      # Check for HTMX archive
      grep -q "hx-post.*archive" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/templates/jobs/list.html && \
      # Check for empty state
      grep -q "No jobs yet" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/templates/jobs/list.html && \
      echo "PASS" || echo "FAIL"
    </automated>
  </verify>
  <done>
    - templates/jobs/list.html created
    - Grid layout with job cards (1 col mobile, 2 col desktop)
    - Status badges with color classes per 01-UI-SPEC.md
    - Job metadata display (title, seniority, salary, industries, company types)
    - Archive button with HTMX POST to /jobs/{id}/archive
    - Edit link to job detail/edit
    - Empty state with icon and CTA
    - Create Job button in header
  </done>
</task>

<task type="auto">
  <name>Task 7: Create job form template for create/edit (JOB-01)</name>
  <files>
    templates/jobs/form.html
  </files>
  <read_first>
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/.planning/phases/01-foundation-job-project-setup/01-UI-SPEC.md (lines 203-219 for form layout)
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/templates/base.html (base template structure)
  </read_first>
  <action>
Create templates/jobs/form.html for job creation and editing (JOB-01):

```html
{% extends "base.html" %}

{% block title %}{% if job %}Edit Job{% else %}Create Job{% endif %} — HR Recruitment AI{% endblock %}

{% block content %}
<div class="mb-8">
    <h2 class="text-4xl font-bold">{% if job %}Edit Job: {{ job.title }}{% else %}Create Job{% endif %}</h2>
    <p class="text-gray-600 mt-2">Define the job position, target industries, and company types for AI-driven candidate hunting</p>
</div>

<div class="bg-white border border-gray-200 rounded-lg p-8 max-w-2xl">
    <form method="POST" hx-post="{% if job %}/jobs/{{ job.id }}{% else %}/jobs{% endif %}" hx-target="body" hx-boost="true">

        <!-- Client selection (required) -->
        <div class="mb-6">
            <label for="client_id" class="block text-sm font-medium text-gray-700 mb-2">Client *</label>
            <select id="client_id" name="client_id" class="form-input" required>
                <option value="">Select a client...</option>
                {% for client in clients %}
                <option value="{{ client.id }}" {% if job and job.client_id == client.id %}selected{% endif %}>
                    {{ client.name }}
                </option>
                {% endfor %}
            </select>
            {% if errors and 'client_id' in errors %}<p class="form-error">{{ errors['client_id'] }}</p>{% endif %}
        </div>

        <!-- Job title (required) -->
        <div class="mb-6">
            <label for="title" class="block text-sm font-medium text-gray-700 mb-2">Job Title *</label>
            <input type="text" id="title" name="title" class="form-input" placeholder="e.g., Senior Software Engineer" value="{{ job.title if job else '' }}" required>
            {% if errors and 'title' in errors %}<p class="form-error">{{ errors['title'] }}</p>{% endif %}
        </div>

        <!-- Description (required) -->
        <div class="mb-6">
            <label for="description" class="block text-sm font-medium text-gray-700 mb-2">Job Description *</label>
            <textarea id="description" name="description" class="form-input" placeholder="Describe the role, responsibilities, and qualifications" rows="6" required>{{ job.description if job else '' }}</textarea>
            {% if errors and 'description' in errors %}<p class="form-error">{{ errors['description'] }}</p>{% endif %}
        </div>

        <!-- Seniority (required) -->
        <div class="mb-6">
            <label for="seniority" class="block text-sm font-medium text-gray-700 mb-2">Seniority Level *</label>
            <select id="seniority" name="seniority" class="form-input" required>
                <option value="">Select seniority...</option>
                <option value="Junior" {% if job and job.seniority == 'Junior' %}selected{% endif %}>Junior</option>
                <option value="Mid-Level" {% if job and job.seniority == 'Mid-Level' %}selected{% endif %}>Mid-Level</option>
                <option value="Senior" {% if job and job.seniority == 'Senior' %}selected{% endif %}>Senior</option>
                <option value="Lead" {% if job and job.seniority == 'Lead' %}selected{% endif %}>Lead</option>
                <option value="Manager" {% if job and job.seniority == 'Manager' %}selected{% endif %}>Manager</option>
                <option value="Director" {% if job and job.seniority == 'Director' %}selected{% endif %}>Director</option>
            </select>
            {% if errors and 'seniority' in errors %}<p class="form-error">{{ errors['seniority'] }}</p>{% endif %}
        </div>

        <!-- Salary range (optional) -->
        <div class="grid grid-cols-2 gap-4 mb-6">
            <div>
                <label for="salary_min" class="block text-sm font-medium text-gray-700 mb-2">Min Salary (USD)</label>
                <input type="number" id="salary_min" name="salary_min" class="form-input" placeholder="e.g., 100000" value="{{ job.salary_min if job else '' }}">
                {% if errors and 'salary_min' in errors %}<p class="form-error">{{ errors['salary_min'] }}</p>{% endif %}
            </div>
            <div>
                <label for="salary_max" class="block text-sm font-medium text-gray-700 mb-2">Max Salary (USD)</label>
                <input type="number" id="salary_max" name="salary_max" class="form-input" placeholder="e.g., 150000" value="{{ job.salary_max if job else '' }}">
                {% if errors and 'salary_max' in errors %}<p class="form-error">{{ errors['salary_max'] }}</p>{% endif %}
            </div>
        </div>

        <!-- Required experience (optional) -->
        <div class="mb-6">
            <label for="required_experience_years" class="block text-sm font-medium text-gray-700 mb-2">Required Experience (years)</label>
            <input type="number" id="required_experience_years" name="required_experience_years" class="form-input" placeholder="e.g., 5" value="{{ job.required_experience_years if job else '' }}">
            {% if errors and 'required_experience_years' in errors %}<p class="form-error">{{ errors['required_experience_years'] }}</p>{% endif %}
        </div>

        <!-- Target industries (optional, JSON array) -->
        <div class="mb-6">
            <label for="target_industries" class="block text-sm font-medium text-gray-700 mb-2">Target Industries</label>
            <input type="text" id="target_industries" name="target_industries" class="form-input" placeholder="e.g., Tech, FinTech, Healthcare (comma-separated)" value="{% if job %}{{ job.target_industries|join(', ') }}{% endif %}">
            <p class="text-xs text-gray-500 mt-1">Enter industries separated by commas</p>
            {% if errors and 'target_industries' in errors %}<p class="form-error">{{ errors['target_industries'] }}</p>{% endif %}
        </div>

        <!-- Target company types (optional, JSON array) -->
        <div class="mb-6">
            <label for="target_company_types" class="block text-sm font-medium text-gray-700 mb-2">Target Company Types</label>
            <input type="text" id="target_company_types" name="target_company_types" class="form-input" placeholder="e.g., Startup, Scale-up, Enterprise (comma-separated)" value="{% if job %}{{ job.target_company_types|join(', ') }}{% endif %}">
            <p class="text-xs text-gray-500 mt-1">Enter company types separated by commas</p>
            {% if errors and 'target_company_types' in errors %}<p class="form-error">{{ errors['target_company_types'] }}</p>{% endif %}
        </div>

        <!-- Form actions -->
        <div class="flex gap-4 pt-6 border-t border-gray-200">
            <button type="submit" class="btn-primary flex-1">
                {% if job %}Update Job{% else %}Create Job{% endif %}
            </button>
            <a href="/jobs" class="btn-secondary flex-1 text-center">Cancel</a>
        </div>
    </form>
</div>

<script>
    // Convert comma-separated strings to JSON arrays before form submission
    document.querySelector('form').addEventListener('submit', function(e) {
        const targetIndustries = document.getElementById('target_industries').value;
        const targetCompanyTypes = document.getElementById('target_company_types').value;

        // Convert to arrays
        document.getElementById('target_industries').value = targetIndustries ? JSON.stringify(targetIndustries.split(',').map(s => s.trim())) : JSON.stringify([]);
        document.getElementById('target_company_types').value = targetCompanyTypes ? JSON.stringify(targetCompanyTypes.split(',').map(s => s.trim())) : JSON.stringify([]);
    });
</script>
{% endblock %}
```

Notes on implementation:
- Form fields match Job model exactly: title, description, seniority, salary_min/max, required_experience_years, target_industries, target_company_types
- Client dropdown populated from clients list
- All required fields marked with * and have required attribute
- Comma-separated input for target_industries and target_company_types (user-friendly)
- JavaScript converts comma-separated strings to JSON arrays before submission
- Error messages displayed below each field (per 01-UI-SPEC.md)
- Textarea for description with 6 rows
- Number inputs for salary and experience
- Cancel link returns to /jobs
- hx-post submits via HTMX, hx-boost handles redirect
  </action>
  <verify>
    <automated>
      # Check form.html exists
      test -f /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/templates/jobs/form.html && \
      # Check extends base
      grep -q "extends.*base" /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/templates/jobs/form.html && \
      # Check for all form fields
      grep -q 'name="title"' /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/templates/jobs/form.html && \
      grep -q 'name="description"' /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/templates/jobs/form.html && \
      grep -q 'name="seniority"' /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/templates/jobs/form.html && \
      grep -q 'name="target_industries"' /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/templates/jobs/form.html && \
      grep -q 'name="target_company_types"' /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/templates/jobs/form.html && \
      # Check for form submission
      grep -q 'hx-post' /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/templates/jobs/form.html && \
      echo "PASS" || echo "FAIL"
    </automated>
  </verify>
  <done>
    - templates/jobs/form.html created
    - Form fields for all Job model attributes
    - Client dropdown (populated from clients list)
    - Required field validation (title, description, seniority, client_id)
    - Comma-separated input for target_industries and target_company_types
    - JavaScript converts arrays before form submission
    - Error message display below each field
    - Save and Cancel buttons
    - HTMX form submission
  </done>
</task>

<task type="auto">
  <name>Task 8: Create routes for form rendering (GET endpoints for create/edit views)</name>
  <files>
    src/app/routes/jobs.py
  </files>
  <read_first>
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/routes/jobs.py (current routes)
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/.planning/phases/01-foundation-job-project-setup/01-UI-SPEC.md (form layout)
  </read_first>
  <action>
Update src/app/routes/jobs.py to add GET endpoints for form rendering:

Add these imports at the top:
```python
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
```

After the imports, add template configuration:
```python
# Template setup
templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))
```

Add these new GET endpoints before the existing POST /jobs create endpoint:

```python
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
    # Deserialize JSON columns for all jobs in case SQLAlchemy returns strings
    import json
    for job in jobs:
        if isinstance(job.target_industries, str):
            job.target_industries = json.loads(job.target_industries) if job.target_industries else []
        if isinstance(job.target_company_types, str):
            job.target_company_types = json.loads(job.target_company_types) if job.target_company_types else []
    
    return templates.TemplateResponse("jobs/list.html", {"request": request, "jobs": jobs})

@router.get("/create", response_class=HTMLResponse)
def job_create_form(
    request: Request,
    session: Session = Depends(get_session),
):
    """Render job creation form"""
    clients = session.exec(select(Client)).all()
    return templates.TemplateResponse("jobs/form.html", {
        "request": request,
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
    return templates.TemplateResponse("jobs/form.html", {
        "request": request,
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
    import json
    if isinstance(job.target_industries, str):
        job.target_industries = json.loads(job.target_industries) if job.target_industries else []
    if isinstance(job.target_company_types, str):
        job.target_company_types = json.loads(job.target_company_types) if job.target_company_types else []
    
    return templates.TemplateResponse("jobs/detail.html", {
        "request": request,
        "job": job,
        "client": client,
    })
```

Note: These are GET endpoints that render HTML templates. The POST endpoints you already created handle the API side.
  </action>
  <verify>
    <automated>
      # Check imports for templates
      grep -q "Jinja2Templates" /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/routes/jobs.py && \
      grep -q "HTMLResponse" /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/routes/jobs.py && \
      # Check template rendering
      grep -q "templates.TemplateResponse.*list.html" /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/routes/jobs.py && \
      grep -q "templates.TemplateResponse.*form.html" /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/routes/jobs.py && \
      echo "PASS" || echo "FAIL"
    </automated>
  </verify>
  <done>
    - src/app/routes/jobs.py updated with GET endpoints for template rendering
    - GET /jobs returns job list dashboard (renders templates/jobs/list.html)
    - GET /jobs/create returns job creation form
    - GET /jobs/{id} returns job detail view
    - GET /jobs/{id}/edit returns job edit form
    - Templates receive request object, jobs/clients data, errors dict
    - All routes properly configured with Jinja2Templates
  </done>
</task>

<task type="auto">
  <name>Task 9: Create job detail template and finalize template structure</name>
  <files>
    templates/jobs/detail.html
    templates/clients/create.html
  </files>
  <read_first>
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/templates/base.html (template structure)
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/.planning/phases/01-foundation-job-project-setup/01-UI-SPEC.md (job detail and form specs)
  </read_first>
  <action>
1. Create templates/jobs/detail.html for job detail view:

```html
{% extends "base.html" %}

{% block title %}Job: {{ job.title }} — HR Recruitment AI{% endblock %}

{% block content %}
<div class="mb-8">
    <div class="flex items-center justify-between mb-4">
        <h2 class="text-4xl font-bold">{{ job.title }}</h2>
        <span class="badge-{{ job.status }} px-4 py-2 rounded-lg text-sm font-medium">
            {{ job.status.replace('_', ' ').title() }}
        </span>
    </div>
    <a href="/jobs" class="text-blue-600 hover:text-blue-700 text-sm">← Back to Jobs</a>
</div>

<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <!-- Main job details -->
    <div class="lg:col-span-2 bg-white border border-gray-200 rounded-lg p-8">
        <!-- Client info -->
        <div class="mb-6 pb-6 border-b border-gray-200">
            <p class="text-sm text-gray-600">Client</p>
            <p class="text-lg font-semibold">{% if client %}{{ client.name }}{% else %}Unknown{% endif %}</p>
        </div>

        <!-- Basic info grid -->
        <div class="grid grid-cols-2 gap-6 mb-8">
            <div>
                <p class="text-sm text-gray-600 mb-1">Seniority Level</p>
                <p class="font-semibold">{{ job.seniority }}</p>
            </div>
            {% if job.required_experience_years %}
            <div>
                <p class="text-sm text-gray-600 mb-1">Required Experience</p>
                <p class="font-semibold">{{ job.required_experience_years }} years</p>
            </div>
            {% endif %}
            {% if job.salary_min or job.salary_max %}
            <div>
                <p class="text-sm text-gray-600 mb-1">Salary Range</p>
                <p class="font-semibold">
                    {% if job.salary_min and job.salary_max %}
                        ${{ job.salary_min|int }}—${{ job.salary_max|int }}
                    {% elif job.salary_min %}
                        ${{ job.salary_min|int }}+
                    {% else %}
                        Up to ${{ job.salary_max|int }}
                    {% endif %}
                </p>
            </div>
            {% endif %}
        </div>

        <!-- Description -->
        <div class="mb-8">
            <h3 class="text-lg font-semibold text-gray-900 mb-3">Job Description</h3>
            <p class="text-gray-700 whitespace-pre-wrap">{{ job.description }}</p>
        </div>

        <!-- Target industries and company types -->
        {% if job.target_industries or job.target_company_types %}
        <div class="mb-8 pb-8 border-b border-gray-200">
            {% if job.target_industries %}
            <div class="mb-4">
                <h4 class="text-sm font-semibold text-gray-700 mb-2">Target Industries</h4>
                <div class="flex flex-wrap gap-2">
                    {% for industry in job.target_industries %}
                    <span class="bg-blue-100 text-blue-900 px-3 py-1 rounded-full text-sm">{{ industry }}</span>
                    {% endfor %}
                </div>
            </div>
            {% endif %}

            {% if job.target_company_types %}
            <div>
                <h4 class="text-sm font-semibold text-gray-700 mb-2">Target Company Types</h4>
                <div class="flex flex-wrap gap-2">
                    {% for company_type in job.target_company_types %}
                    <span class="bg-green-100 text-green-900 px-3 py-1 rounded-full text-sm">{{ company_type }}</span>
                    {% endfor %}
                </div>
            </div>
            {% endif %}
        </div>
        {% endif %}

        <!-- Timestamps -->
        <div class="text-xs text-gray-500">
            <p>Created: {{ job.created_at.strftime('%Y-%m-%d %H:%M:%S') }}</p>
            <p>Last updated: {{ job.updated_at.strftime('%Y-%m-%d %H:%M:%S') }}</p>
        </div>
    </div>

    <!-- Sidebar actions -->
    <div class="lg:col-span-1">
        <div class="bg-gray-50 border border-gray-200 rounded-lg p-6 sticky top-24">
            <h3 class="font-semibold text-gray-900 mb-4">Actions</h3>

            <a href="/jobs/{{ job.id }}/edit" class="btn-secondary w-full text-center mb-3">Edit Job</a>

            <button hx-post="/jobs/{{ job.id }}/archive" hx-target="body" class="btn-destructive w-full" onclick="return confirm('Archive this job? You can reopen it anytime.')">
                Archive Job
            </button>
        </div>
    </div>
</div>
{% endblock %}
```

2. Create templates/clients/create.html for minimal client creation (optional for Phase 1, but good to have):

```html
{% extends "base.html" %}

{% block title %}Create Client — HR Recruitment AI{% endblock %}

{% block content %}
<div class="mb-8">
    <h2 class="text-4xl font-bold">Create Client</h2>
    <p class="text-gray-600 mt-2">Add a new client to assign jobs</p>
</div>

<div class="bg-white border border-gray-200 rounded-lg p-8 max-w-md">
    <form method="POST" action="/clients" hx-post="/clients" hx-target="body" hx-boost="true">
        <div class="mb-6">
            <label for="name" class="block text-sm font-medium text-gray-700 mb-2">Client Name *</label>
            <input type="text" id="name" name="name" class="form-input" placeholder="e.g., Acme Inc." required>
        </div>

        <div class="flex gap-4">
            <button type="submit" class="btn-primary flex-1">Create Client</button>
            <a href="/" class="btn-secondary flex-1 text-center">Cancel</a>
        </div>
    </form>
</div>
{% endblock %}
```
  </action>
  <verify>
    <automated>
      # Check detail.html exists
      test -f /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/templates/jobs/detail.html && \
      # Check extends base
      grep -q "extends.*base" /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/templates/jobs/detail.html && \
      # Check client creation template
      test -f /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/templates/clients/create.html && \
      echo "PASS" || echo "FAIL"
    </automated>
  </verify>
  <done>
    - templates/jobs/detail.html created with job details, client info, salary range
    - Job description displayed in readable format
    - Target industries/company types shown as tags
    - Edit and Archive actions in sidebar
    - Timestamps displayed
    - templates/clients/create.html created for minimal client creation
    - All templates follow 01-UI-SPEC.md design system
  </done>
</task>

<task type="auto">
  <name>Task 10: Add API route for handling form POST requests (create/update/archive)</name>
  <files>
    src/app/routes/jobs.py
  </files>
  <read_first>
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/routes/jobs.py (current routes)
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/templates/jobs/form.html (form submission)
  </read_first>
  <action>
Update src/app/routes/jobs.py to handle form-based requests (not just JSON API):

Add imports at top if not present:
```python
from fastapi import Form
from fastapi.responses import RedirectResponse
```

Add these new POST endpoints after the existing API endpoints:

```python
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
```

Also update the existing POST /jobs endpoint to handle JSON API requests if they come in:

```python
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
```

Alternatively, modify the existing POST /jobs to detect request content type and handle both form and JSON.
  </action>
  <verify>
    <automated>
      # Check form parsing logic
      grep -q "Form(" /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/routes/jobs.py && \
      grep -q "split(',')" /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/routes/jobs.py && \
      # Check redirect response
      grep -q "RedirectResponse" /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/routes/jobs.py && \
      echo "PASS" || echo "FAIL"
    </automated>
  </verify>
  <done>
    - POST / endpoint updated to handle form-encoded requests (from HTML form)
    - Form fields converted from strings to proper types (comma-separated → lists)
    - Redirects to job detail on success (status 303 See Other)
    - Error handling redirects back to form
    - Separate POST /api endpoint for JSON API requests
    - Both endpoints populate target_industries and target_company_types correctly
  </done>
</task>

</tasks>

<verification>
After Plan 02 execution:

1. **Routes created:** Jobs and clients routers registered in main FastAPI app
2. **API endpoints working:**
   - POST /jobs (create job) — accepts form data
   - GET /jobs (list jobs dashboard) — returns HTML
   - GET /jobs/{id} (job detail) — returns HTML
   - POST /jobs/{id}/archive (archive job) — accepts form POST via HTMX
3. **Templates rendered:** All Jinja2 templates parse correctly
4. **Tailwind CSS applied:** Base template includes CDN, pages have proper styling
5. **HTMX wired:** Archive button uses hx-post, form uses HTMX for submission
6. **Form validation:** Required fields validated server-side, errors displayed below fields
7. **Redirects work:** Form submissions redirect to job detail page on success
8. **Dashboard displays:** Job list shows active jobs with status badges, industry/company type tags
9. **UI matches spec:** Colors, spacing, fonts follow 01-UI-SPEC.md
</verification>

<success_criteria>
- [ ] src/app/schemas.py created with Pydantic request/response schemas
- [ ] src/app/routes/clients.py created with POST /clients and GET /clients
- [ ] src/app/routes/jobs.py created with all job CRUD routes (create, list, detail, update, archive)
- [ ] src/app/routes/jobs.py has GET endpoints to render templates
- [ ] src/app/main.py updated to include_router for jobs and clients
- [ ] templates/base.html created with Tailwind CDN and HTMX
- [ ] templates/jobs/list.html renders job dashboard with status badges and archive HTMX
- [ ] templates/jobs/form.html has all required job fields (title, description, seniority, salary, industries, company types)
- [ ] templates/jobs/detail.html displays full job details with edit and archive actions
- [ ] templates/clients/create.html created for minimal client creation
- [ ] Form submissions POST to /jobs and redirect to detail view
- [ ] Archive button uses HTMX POST to /jobs/{id}/archive
- [ ] UI passes 01-UI-SPEC.md design system (colors, spacing, typography)
- [ ] Empty state displayed when no jobs exist
- [ ] Target industries and company types properly rendered (from JSON lists)

Requirement coverage:
- JOB-01: Consultant can create job with title, description, seniority, salary, experience ✓
- JOB-02: Job form includes target_industries and target_company_types fields ✓
- JOB-03: Dashboard displays all active jobs with status badges ✓
- JOB-04: Consultant can archive jobs via HTMX button ✓
</success_criteria>

<output>
After completion, create `.planning/phases/01-foundation-job-project-setup/02-PLAN-SUMMARY.md`
</output>
