# Phase 1 Context: Foundation — Job & Project Setup

**Phase:** 1
**Created:** 2026-03-23
**Status:** Ready for planning

---

## Decisions

### Database Layer

**ORM:** SQLModel (SQLAlchemy + Pydantic v2 combined)
- Models are both Pydantic-validated and SQLAlchemy-mapped
- No separate schema/model duplication
- All AI agent inputs/outputs are already Pydantic models — consistent throughout

**Database target:** SQLite for v1, Postgres-compatible path for v2
- SQLite for local development (single file, zero services)
- Design all models to be Postgres-compatible (no SQLite-specific types, no raw JSON tricks)
- Postgres support added at VPS deployment stage (v2)

---

### Data Model Scope

**Client entity:** Separate `Client` table (not free-text on Job)
- Job belongs_to Client via `client_id` FK
- Required Client fields: `id`, `name`, `created_at`
- Enables client history even in v1
- Phase 1 includes a minimal client creation flow (name only — no full CRUD screen)

**JOB-02 target industries / company types:** JSON list columns on Job
- `target_industries: list[str]` stored as JSON in SQLite
- `target_company_types: list[str]` stored as JSON in SQLite
- SQLModel handles serialization via `Field(default=[], sa_column=Column(JSON))`
- No separate tags table in v1 — upgrade path deferred to v2

---

### Frontend Stack

**Approach:** HTMX + Jinja2 + Tailwind CSS (CDN)
- FastAPI serves Jinja2 templates (no separate SPA)
- HTMX for partial page updates (job creation, status changes, archive) without full reloads
- Tailwind CSS via CDN — no build step
- No JavaScript build pipeline in Phase 1

**Why not SPA:** Single-consultant internal tool, no need for the complexity overhead.

---

### Project Tooling

**Package manager:** `uv`
- `uv init` for project scaffold
- `uv add` for dependencies
- `uv run uvicorn app.main:app --reload` for dev server

**Docker:** Not in Phase 1
- SQLite is a single file — no services to containerize
- Run directly with `uv run` locally
- Docker added at VPS deployment stage

---

## Phase 1 Scope Constraints

These are in scope for Phase 1:
- Client model + minimal creation (name field only)
- Job model with all JOB-01 fields + JSON industry/company-type lists
- Job create/edit/archive (JOB-01, JOB-04)
- Job list dashboard with pipeline status display (JOB-03)
- HTMX + Jinja2 frontend for the above
- SQLModel + SQLite database with Alembic migrations

These are explicitly out of scope for Phase 1:
- Full Client CRUD / client list screen
- AI agents (Phase 2+)
- Candidate model (Phase 3)
- Outreach tracking (Phase 2)
- Export / PDF (Phase 3)

---

## Key Models (Reference for Planner)

```python
class Client(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Job(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.id")
    title: str
    description: str
    seniority: str  # e.g. "Senior", "Manager", "Director"
    salary_min: int | None = None
    salary_max: int | None = None
    required_experience_years: int | None = None
    target_industries: list[str] = Field(default=[], sa_column=Column(JSON))
    target_company_types: list[str] = Field(default=[], sa_column=Column(JSON))
    status: JobStatus = JobStatus.hunting
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class JobStatus(str, Enum):
    hunting = "hunting"
    shortlisting = "shortlisting"
    interviewing = "interviewing"
    closed = "closed"
```

---

## Existing Prototype Reference

The existing `hr-platform` project at `../hr-platform` has:
- Raw `sqlite3` database layer (no ORM) — **do not reuse, rewrite with SQLModel**
- Pydantic v2 models in `src/hr_platform/models/schema.py` — review for field ideas only
- SQL schema in `migrations/001_initial.sql` — reference for field names, not for copy-paste

The new project is a **clean rebuild**, not a migration.

---

## Deferred Ideas

- Full Client CRUD screen with client list → Phase 2+ or when a second client is added
- Tags/taxonomy table for industries → v2 when cross-job filtering is needed
- Docker Compose → VPS deployment phase
- Postgres → v2 deployment
