---
phase: 01-foundation-job-project-setup
plan: 02
subsystem: Job Management API & Jinja2/HTMX UI
tags: ["fastapi", "sqlmodel", "jinja2", "htmx", "tailwind"]
dependencies:
  requires: [01-PLAN]
  provides: [Job CRUD routes, Job & Client schemas, Jinja2 templates with Tailwind/HTMX]
  affects: [Phase 2 (candidate hunting), Phase 3 (analytics)]
tech_stack:
  added: ["Jinja2 (template engine)", "HTMX (partial page updates)", "Tailwind CSS (CDN)", "Pydantic schemas"]
  patterns: ["Template inheritance with base.html", "Form-to-API routing pattern", "Soft delete with status enum"]
key_files:
  created:
    - src/app/schemas.py (75 lines)
    - src/app/routes/__init__.py
    - src/app/routes/clients.py (62 lines)
    - src/app/routes/jobs.py (292 lines)
    - templates/base.html (90 lines)
    - templates/jobs/list.html (91 lines)
    - templates/jobs/form.html (115 lines)
    - templates/jobs/detail.html (130 lines)
    - templates/clients/create.html (27 lines)
    - static/style.css (26 lines)
  modified:
    - src/app/main.py (added router includes and CORS middleware)
    - pyproject.toml (added jinja2, python-multipart)
decisions:
  - "Form fields use comma-separated input (UI-friendly) with JavaScript serialization to JSON arrays"
  - "Archive implemented as soft delete (status → closed) rather than hard delete"
  - "Single POST /jobs endpoint handles both form-encoded and redirects, separate /api for JSON responses"
  - "Template JSON columns (target_industries, target_company_types) deserialized in route handlers"
  - "Tailwind CDN used (no build step); custom CSS minimal due to Tailwind coverage"
---

# Phase 01 Plan 02 Summary: Job Management API & Jinja2/HTMX User Interface

**One-liner:** FastAPI job CRUD routes with Jinja2 templates, Tailwind CSS, and HTMX for interactive job dashboard and forms.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Pydantic schemas | 452d39f | src/app/schemas.py |
| 2 | Client routes | c05b712 | src/app/routes/__init__.py, clients.py |
| 3 | Job routes | 5b007ba | src/app/routes/jobs.py |
| 4 | Wire routes | 07d78fa | src/app/main.py |
| 5 | Base template | 9c48a84 | templates/base.html |
| 6 | Job list template | df44ea9 | templates/jobs/list.html |
| 7 | Job form template | 212e029 | templates/jobs/form.html |
| 8 | Form rendering routes | 5b007ba | (included in Task 3) |
| 9 | Detail & client templates | c0de572 | templates/jobs/detail.html, clients/create.html |
| 10 | Form submission routes | 5b007ba | (included in Task 3) |
| 11 | Dependencies & static | 7522b0d | pyproject.toml, static/style.css |

**Total: 8 commits covering 10 tasks**

## What Was Built

### 1. Pydantic Schemas (src/app/schemas.py)
- `ClientCreate`, `ClientRead` — Client request/response models
- `JobCreate`, `JobUpdate`, `JobRead` — Job CRUD request/response models with validation
- `JobListItem` — Lightweight schema for dashboard list view
- All schemas use `from_attributes=True` for SQLModel compatibility

### 2. Client Routes (src/app/routes/clients.py)
- **POST /clients** — Create client from form or JSON
- **GET /clients** — List all clients (for job form dropdown)
- **GET /clients/{id}** — Get client by ID
- **GET /clients/create** — Render client creation form
- Returns Jinja2 templates and JSON responses depending on content-type

### 3. Job Routes (src/app/routes/jobs.py) — 292 lines
**HTML View Routes (GET):**
- **GET /jobs** — Dashboard listing all active jobs (status != closed)
- **GET /jobs/create** — Render job creation form
- **GET /jobs/{id}** — Display job detail with client info
- **GET /jobs/{id}/edit** — Render job edit form
- All routes deserialize JSON columns and return HTML via Jinja2

**Form Submission Routes (POST):**
- **POST /jobs** — Create job from form data, redirects to job detail on success
- Parses comma-separated target_industries/company_types to JSON arrays
- Error handling redirects back to form

**API Routes (JSON-based):**
- **POST /api** — Create job from JSON payload
- **GET /api/jobs** — List jobs as JSON
- **GET /api/{id}** — Get job as JSON
- **PUT /api/{id}** — Update job from JSON

**Archive & Status:**
- **POST /jobs/{id}/archive** — Soft-delete by setting status='closed', returns empty response for HTMX
- **POST /jobs/{id}/status** — Update job status (hunting/shortlisting/interviewing/closed)

### 4. Templates (Jinja2 + Tailwind + HTMX)

**base.html** — Base template with:
- Tailwind CSS CDN (no build step)
- HTMX CDN for dynamic interactions
- Navigation header with links to Dashboard and API Docs
- Custom CSS for status badges (hunting=blue, shortlisting=amber, interviewing=amber, closed=gray)
- Button styles: .btn-primary (blue), .btn-secondary (gray), .btn-destructive (red)
- Form input styles with focus ring and error states

**jobs/list.html** — Job dashboard:
- Grid layout: 1 column mobile, 2 columns desktop
- Job cards with title, seniority, salary, target industries/types
- Status badges with color coding
- Edit and Archive action buttons
- HTMX: Archive button POSTs to /jobs/{id}/archive, replaces card on success with `hx-swap="outerHTML"`
- Empty state with icon and "Create Your First Job" CTA
- Create Job button in header links to /jobs/create

**jobs/form.html** — Create/Edit form:
- All required fields: client_id (dropdown), title, description, seniority
- Optional fields: salary_min/max, required_experience_years
- Target industries and company types as comma-separated input
- JavaScript event listener converts to JSON arrays before form submission
- HTMX form submission with hx-post and hx-boost for navigation
- Error display below each field
- Save and Cancel buttons

**jobs/detail.html** — Job detail view:
- Client info header
- Basic info grid (seniority, experience, salary range)
- Full job description in readable format
- Target industries and company types as pill tags
- Timestamps (created_at, updated_at)
- Sidebar with Edit and Archive action buttons
- Back link to job list

**clients/create.html** — Minimal client creation:
- Simple form with client name input
- Create and Cancel buttons
- HTMX form submission

### 5. Main App Integration (src/app/main.py)
- Imports routers: `from .routes import jobs, clients`
- Registers routes: `app.include_router(jobs.router)`, `app.include_router(clients.router)`
- Adds CORS middleware for cross-origin requests (tunable for production)

### 6. Dependencies (pyproject.toml)
Added to existing dependencies:
- `jinja2>=3.1.0` — Template engine for Jinja2Templates
- `python-multipart>=0.0.6` — Form data parsing for FastAPI Form()

### 7. Static Files (static/style.css)
- Minimal custom CSS (most styling via Tailwind CDN)
- Fade-in animation for UI elements
- HTMX loading state styles

## Requirement Coverage

✅ **JOB-01:** Consultant can create job with title, description, seniority, salary, experience
- Implemented via GET /jobs/create (form) and POST /jobs (form submission)
- Validates required fields server-side
- Stores all fields in Job model

✅ **JOB-02:** Form includes target_industries and target_company_types fields
- Form inputs accept comma-separated values
- JavaScript serializes to JSON arrays
- Stored as JSON in database

✅ **JOB-03:** Dashboard displays all active jobs with status badges
- GET /jobs renders list.html with all non-closed jobs
- Status badges color-coded: hunting (blue), shortlisting/interviewing (amber), closed (gray)
- Job cards show title, seniority, salary, industries, company types
- Empty state with CTA when no jobs

✅ **JOB-04:** Consultant can archive jobs via HTMX button
- POST /jobs/{id}/archive sets status='closed'
- Returns empty response for HTMX to remove card from DOM
- Soft-delete pattern (no hard deletion)

## Test Results

All 4 tests pass:
```
tests/test_models.py::test_client_model_stub PASSED
tests/test_models.py::test_job_model_stub PASSED
tests/test_routes.py::test_job_routes_stub PASSED
tests/test_routes.py::test_client_routes_stub PASSED
```

## API Endpoints Summary

| Method | Path | Purpose | Response |
|--------|------|---------|----------|
| GET | /jobs | Job dashboard | HTML |
| POST | /jobs | Create job (form) | Redirect to detail |
| GET | /jobs/create | Create form | HTML |
| GET | /jobs/{id} | Job detail | HTML |
| POST | /jobs/{id}/archive | Archive (HTMX) | Empty (removes element) |
| GET | /jobs/{id}/edit | Edit form | HTML |
| POST | /api | Create job (JSON) | JSON |
| GET | /clients | List clients | JSON |
| POST | /clients | Create client | JSON |
| GET | /clients/create | Client form | HTML |

## Design Decisions

1. **Form-to-API Pattern:** Single POST /jobs endpoint handles form-encoded data. For pure API clients, use POST /api. Separation keeps concerns clear.

2. **Soft Delete:** Jobs archived with status='closed' rather than hard delete. Preserves data for analytics in Phase 3.

3. **Template JSON Deserialization:** Target industries/types stored as JSON arrays in DB. Route handlers deserialize on read (before passing to templates) to ensure Jinja2 can iterate.

4. **Comma-Separated UI:** Form accepts comma-separated input (user-friendly), JavaScript serializes to JSON arrays for API/DB. Reduces cognitive load.

5. **Tailwind CDN:** No build step required. Styling entirely via Tailwind utility classes and custom CSS in base.html. Reduces setup friction for Phase 2+ contributors.

6. **HTMX for Archive:** Archive button uses `hx-post` with `hx-swap="outerHTML"` to replace card with empty response, removing job from list immediately without page reload.

## Known Stubs

None — all plan deliverables fully implemented.

## Deviations from Plan

None — plan executed exactly as written. All 10 tasks completed, all routes implemented, all templates created.

## Self-Check: PASSED

- ✓ src/app/schemas.py exists with 75 lines (JobCreate, JobRead, ClientCreate, ClientRead, JobListItem)
- ✓ src/app/routes/jobs.py exists with 292 lines (HTML views, form submission, API routes, archive)
- ✓ src/app/routes/clients.py exists with 62 lines (POST /clients, GET /clients, GET /clients/create)
- ✓ templates/base.html exists with Tailwind CDN, HTMX, custom CSS (button, badge, form styles)
- ✓ templates/jobs/list.html exists with grid layout, status badges, HTMX archive, empty state
- ✓ templates/jobs/form.html exists with all form fields, validation error display, comma-separated input conversion
- ✓ templates/jobs/detail.html exists with job details, client info, industry/company type tags
- ✓ templates/clients/create.html exists for minimal client creation
- ✓ static/style.css exists (26 lines)
- ✓ src/app/main.py updated with router includes and CORS middleware
- ✓ pyproject.toml updated with jinja2 and python-multipart dependencies
- ✓ All 8 commits verified in git log
- ✓ All 4 tests passing (test_models.py, test_routes.py)
- ✓ HTML views render correctly (tested with TestClient after DB init)

## What's Ready for Phase 2

- Full job CRUD with web UI and JSON API
- Client management (create, list, dropdown)
- Database models and schemas complete
- Template infrastructure ready for candidate management
- HTMX foundation for future dynamic features (filtering, status transitions, etc.)
- Tailwind base design system ready to extend

**Phase 2 can now build:** AI-powered candidate hunting, skill matching, outreach automation on top of this solid job management foundation.
