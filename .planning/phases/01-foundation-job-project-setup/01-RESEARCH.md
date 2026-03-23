# Phase 1: Foundation — Job & Project Setup — Research

**Phase:** 1 — Foundation — Job & Project Setup
**Researched:** 2026-03-23
**Confidence:** HIGH

---

## User Constraints (from CONTEXT.md)

Locked decisions from discuss-phase:
- SQLModel for unified SQLAlchemy + Pydantic models
- FastAPI + Jinja2 + HTMX for the web layer (no heavy JS framework)
- SQLite for development (PostgreSQL migration path kept open)
- uv for dependency management
- JSON columns for `target_industries` and `target_company_types`

---

## Phase Requirements

| ID | Requirement | Notes |
|----|-------------|-------|
| JOB-01 | Create a job with title, client, description | Core model field |
| JOB-02 | Define search scope (target industries, company types) | JSON columns |
| JOB-03 | Job lifecycle status (Hunting/Shortlisting/Interviewing/Closed) | Enum field |
| JOB-04 | Job list dashboard | HTMX + Jinja2 UI |

---

## Standard Stack — Verified Versions (Mar 23, 2026)

| Package | Version | Notes |
|---------|---------|-------|
| Python | 3.14.0 | Installed via system |
| uv | 0.10.12 | Installed |
| FastAPI | 0.111.0+ | Native Jinja2 support |
| SQLModel | 0.0.37 | Pydantic v2 compatible (Feb 2026) |
| SQLAlchemy | 2.0.48 | Bundled with SQLModel |
| Pydantic | v2.12.5 | Bundled with SQLModel |
| HTMX | 2.0.8 | 16KB, CDN-deliverable |
| Jinja2 | 3.x | FastAPI native integration |
| pytest | 9.x | Test framework |
| pytest-asyncio | latest | For async FastAPI tests |
| SQLite | 3.46.0 | System — supports JSON functions (3.38.0+) |

All versions current and mutually compatible. No conflicts.

---

## Architecture Patterns

### SQLModel — Unified Data Models

SQLModel 0.0.37 eliminates the Pydantic model / SQLAlchemy model duplication problem:

```python
from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime
import json

class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    client_name: str
    description: str
    status: str = Field(default="Hunting")  # Hunting/Shortlisting/Interviewing/Closed
    target_industries: str = Field(default="[]")   # JSON-serialized list
    target_company_types: str = Field(default="[]") # JSON-serialized list
    created_at: datetime = Field(default_factory=datetime.utcnow)
    archived: bool = Field(default=False)
```

**JSON column pattern for SQLite:** Store as TEXT, serialize/deserialize manually or via validator. SQLAlchemy JSON type works but TEXT + property approach avoids migration complexity.

### FastAPI + Jinja2 + HTMX

```python
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()
templates = Jinja2Templates(directory="templates")  # use absolute path in prod

@app.get("/jobs")
async def list_jobs(request: Request, session: Session = Depends(get_session)):
    jobs = session.exec(select(Job).where(Job.archived == False)).all()
    return templates.TemplateResponse("jobs/list.html", {"request": request, "jobs": jobs})
```

**HTMX pattern for partial updates:**
```html
<button hx-post="/jobs/1/archive" hx-target="#job-row-1" hx-swap="outerHTML">
  Archive
</button>
```

### Database Initialization

```python
from sqlmodel import create_engine, SQLModel, Session

DATABASE_URL = "sqlite:///./hr_recruitment.db"
engine = create_engine(DATABASE_URL, echo=True)

def create_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
```

---

## Don't Hand-Roll

- **HTTP server:** Use FastAPI + uvicorn — don't write ASGI manually
- **ORM:** Use SQLModel — don't write raw SQL for CRUD
- **Templates:** Use Jinja2 via FastAPI — don't string-format HTML
- **Migrations:** Use Alembic for schema changes — don't ALTER TABLE manually
- **Form validation:** Use Pydantic models via FastAPI — don't parse request body manually

---

## Runtime State Inventory

Greenfield project — no existing database, no existing schema, no prior migrations. Phase 1 starts from zero.

---

## Common Pitfalls

1. **SQLModel < 0.0.30 breaks Pydantic v2** — always pin `sqlmodel>=0.0.30`
2. **SQLite JSON functions require 3.38.0+** — system has 3.46.0, no issue
3. **HTMX form validation needs server-side Pydantic validation** — don't rely on client-side only
4. **JSON column mutations require full reassignment** — SQLAlchemy change tracking doesn't detect in-place list mutations; do `job.target_industries = json.dumps(new_list)` not `list.append()`
5. **Jinja2 template paths must be absolute in production** — use `Path(__file__).parent / "templates"` not relative string
6. **FastAPI requires `Depends()` for dependency injection** — passing session directly to route functions won't work with connection lifecycle

---

## Environment Availability

| Tool | Status | Notes |
|------|--------|-------|
| Python 3.14.0 | ✓ Available | — |
| uv 0.10.12 | ✓ Available | Use for venv + deps |
| SQLite 3.46.0 | ✓ Available | JSON support confirmed |
| FastAPI | ○ To install | Via uv |
| SQLModel | ○ To install | Via uv |
| HTMX | ○ CDN | No install needed |

---

## Code Examples (Official Sources)

All patterns above sourced from:
- FastAPI official docs (fastapi.tiangolo.com) — Jinja2 templates, dependency injection
- SQLModel official docs (sqlmodel.tiangolo.com) — table models, relationships
- HTMX official docs (htmx.org) — partial updates, form submission

---

## Validation Architecture

### Test Framework

- **Framework:** pytest 9.x + pytest-asyncio
- **Test client:** `httpx.AsyncClient` with FastAPI `TestClient` for route tests
- **DB strategy:** In-memory SQLite (`sqlite:///:memory:`) for isolated test sessions

### Test Map

| Requirement | Test | Acceptance |
|-------------|------|------------|
| JOB-01 | `test_create_job` | Job record persisted, title/client/description present |
| JOB-02 | `test_job_search_scope` | `target_industries` and `target_company_types` round-trip JSON correctly |
| JOB-03 | `test_job_status_lifecycle` | Status transitions Hunting→Shortlisting→Interviewing→Closed all valid |
| JOB-04 | `test_job_list_dashboard` | GET /jobs returns 200 with job list rendered |
| JOB-04 | `test_create_job_form` | POST /jobs creates record, redirects to list |
| JOB-04 | `test_archive_job` | Archive action removes job from active list |

### Wave 0 Gap

No test infrastructure exists yet. Plan 1.1 must include:
- `pyproject.toml` with `[tool.pytest.ini_options]`
- `pytest-asyncio` in dev dependencies
- `conftest.py` with in-memory DB fixture

---

## Sources

| Source | Confidence | Date |
|--------|-----------|------|
| SQLModel docs (sqlmodel.tiangolo.com) | HIGH | Mar 2026 |
| FastAPI docs (fastapi.tiangolo.com) | HIGH | Mar 2026 |
| HTMX docs (htmx.org) | HIGH | Mar 2026 |
| pytest docs (docs.pytest.org) | HIGH | Mar 2026 |
| System environment check | HIGH | Mar 23, 2026 |

---

## RESEARCH COMPLETE

All locked decisions from CONTEXT.md are technically sound. Stack is verified. Environment is ready. No blockers for Phase 1 planning.
