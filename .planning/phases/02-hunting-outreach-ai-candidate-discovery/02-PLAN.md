---
phase: 02-hunting-outreach-ai-candidate-discovery
plan: 02
type: execute
wave: 2
depends_on: [01]
files_modified:
  - src/app/routes/jobs.py
  - src/app/routes/hunting.py
  - src/app/agents/role_identifier.py
  - templates/jobs/detail.html
  - templates/jobs/hunting-companies.html
  - templates/jobs/hunting-candidates.html
  - tests/test_hunting_routes.py
  - static/style.css
autonomous: true
requirements: [HUNT-01, HUNT-02, HUNT-03, HUNT-04]
user_setup: []

must_haves:
  truths:
    - "Consultant can click 'Start Hunting' button on job detail page and see it initiate company mapping via AI agent"
    - "Company cards display with name, industry, size, and LinkedIn link (from TargetCompany records)"
    - "Consultant can see candidate cards progressively as RoleIdentifierAgent discovers candidates"
    - "Each candidate card shows: name, current title, company, LinkedIn URL, email, status badge"
    - "Consultant can approve or reject candidates via buttons; status updates immediately"
    - "Approved candidates move to next phase for outreach drafting (Plan 03)"
  artifacts:
    - path: "src/app/routes/hunting.py"
      provides: "FastAPI routes for hunting workflows: start_hunting, get_hunting_session, list_companies, approve_candidate"
      exports: ["router", "start_hunting", "get_companies", "approve_candidate", "reject_candidate"]
      min_lines: 200
    - path: "src/app/agents/role_identifier.py"
      provides: "RoleIdentifierAgent that discovers candidates at target companies"
      exports: ["RoleIdentifierAgent", "RoleIdentifierRequest", "RoleIdentifierResponse"]
      min_lines: 120
    - path: "templates/jobs/hunting-companies.html"
      provides: "Company list view template with add/remove actions, linked from job detail"
      min_lines: 50
    - path: "templates/jobs/hunting-candidates.html"
      provides: "Candidate review template with status badges, approve/reject buttons, HTMX integration"
      min_lines: 100
    - path: "tests/test_hunting_routes.py"
      provides: "Integration tests for hunting routes: start, list, approve, reject"
      min_lines: 120
    - path: "static/style.css"
      provides: "Status badge CSS classes for Phase 2: hunting, approved, rejected, pending_outreach, sent, replied, not_interested"
      min_lines: 20
  key_links:
    - from: "templates/jobs/detail.html"
      to: "src/app/routes/hunting.py"
      via: "'Start Hunting' button posts to /jobs/{id}/hunting/start via HTMX"
      pattern: "hx-post.*hunting/start"
    - from: "src/app/routes/hunting.py"
      to: "src/app/agents/company_mapper.py"
      via: "start_hunting route calls CompanyMapperAgent.run() via BackgroundTasks"
      pattern: "CompanyMapperAgent.*run"
    - from: "src/app/routes/hunting.py"
      to: "src/app/agents/role_identifier.py"
      via: "After companies created, RoleIdentifierAgent.run() discovers candidates per company"
      pattern: "RoleIdentifierAgent.*run"
    - from: "templates/jobs/hunting-candidates.html"
      to: "src/app/routes/hunting.py"
      via: "Approve/Reject buttons POST to /hunting/{session_id}/candidates/{id}/approve|reject"
      pattern: "hx-post.*candidates.*approve"

---

<objective>
Build the hunting UI and route layer for Phase 2. This plan adds: (1) FastAPI routes for starting hunting sessions, listing discovered companies, and approving/rejecting candidates, (2) a RoleIdentifierAgent that finds candidates at target companies using Claude, (3) Jinja2 templates for company and candidate review with HTMX interactions, and (4) integration tests for the hunting workflow.

Purpose: This is the bridge between the job detail page (Phase 1) and the approval flow. Consultant clicks "Start Hunting" on a job, AI generates companies and candidates, and consultant reviews and approves them before outreach drafting happens in Plan 03.

Output: Working hunting workflow with company targeting UI, candidate discovery UI, and HTMX-driven approval flow.
</objective>

<context>
From Plan 01 (this phase):
- HuntingSession, TargetCompany, Candidate models created
- CompanyMapperAgent working (generates companies)
- BaseAgent pattern established for reuse
- Test infrastructure ready for integration tests

Phase 1 foundation:
- Job routes exist at /jobs/{id}
- Jinja2 templates with Tailwind CSS
- HTMX 2.0.8 integrated
- Form patterns established (btn-primary, btn-secondary, form-input classes)

Phase 2 UI contract (from UI-SPEC.md):
- "Start Hunting" button: primary blue, placed on job detail sidebar
- Company cards: white bg, border-gray-200, p-4, show name/industry/size/LinkedIn
- Candidate cards: same pattern, show name/title/company/LinkedIn/email, status badge
- Status badges: hunting (cyan), approved (green), rejected (red)
- HTMX patterns: `hx-post` for triggers, `hx-target` for progressive updates

Key integration patterns:
- BackgroundTasks for async agent runs (don't block HTTP response)
- Session-based hunting (one session per start_hunting call)
- Progressive rendering (companies appear as TargetCompany records created, then candidates)
- Approval flow (candidate.status changes on approve/reject)
</context>

<tasks>

## Task 1: Add hunting routes to FastAPI app

**Files:** src/app/routes/hunting.py

**Action:** Create new router module with the following endpoints:

1. **POST /jobs/{job_id}/hunting/start**
   - Start a new hunting session for a job
   - Create HuntingSession record with status=pending
   - Queue CompanyMapperAgent.run() via BackgroundTasks
   - Return redirect to /jobs/{job_id}/hunting (hunting detail page)
   - Error handling: If job not found, 404. If hunting already in progress, show warning but allow new run.

2. **GET /jobs/{job_id}/hunting**
   - Render hunting detail page (template: hunting-companies.html)
   - Query latest HuntingSession for this job (order by created_at desc)
   - Get all TargetCompany records for that session
   - Get all Candidate records for that session (with status)
   - Pass to template: job, hunting_session, companies, candidates

3. **GET /jobs/{job_id}/hunting/companies**
   - Return HTML fragment of company cards (for HTMX polling during "Hunting..." state)
   - Query TargetCompany records for latest session
   - Return as company card fragments (re-render every 2-3 seconds via HTMX polling)

4. **GET /jobs/{job_id}/hunting/candidates**
   - Return HTML fragment of candidate cards (for HTMX polling)
   - Query Candidate records for latest session (order by created_at desc)
   - Return as candidate card fragments

5. **POST /hunting/{session_id}/candidates/{candidate_id}/approve**
   - Update Candidate.status = "approved"
   - Return empty response (HTMX-driven, card fades/moves)
   - If filtering by status, redirect consumer to refresh

6. **POST /hunting/{session_id}/candidates/{candidate_id}/reject**
   - Update Candidate.status = "rejected"
   - Return empty response

7. **POST /hunting/{session_id}/companies/{company_id}/remove**
   - Delete TargetCompany record
   - Return empty response (HTMX removes DOM element)

**Integration with Phase 1:**
- Import job routes, extend with hunting sub-routes under /jobs
- Add hunting router to main.py: `app.include_router(hunting.router)`

**Validation:** All routes use proper HTTP status codes (201 for creation, 404 for not found, 200 for updates). Session management via SQLModel session dependency. Error responses include descriptive messages.

## Task 2: Extend jobs.py detail view to include "Start Hunting" button

**Files:** src/app/routes/jobs.py

**Action:** Modify the existing `job_detail_view` route:

1. Add "Start Hunting" button to the sidebar actions (alongside "Edit Job", "Archive Job")
2. Button should:
   - Be primary blue (btn-primary class)
   - Post to /jobs/{id}/hunting/start via HTMX (hx-post, hx-target="body")
   - Have loading state: `hx-indicator="#hunting-spinner"` with a spinner div
   - Disable button while hunting is in progress (check if latest HuntingSession.status == "in_progress")

**Template change:** In jobs/detail.html, add:
```html
<button hx-post="/jobs/{{ job.id }}/hunting/start"
        hx-target="#hunting-container"
        class="btn-primary w-full mb-3">
  Start Hunting
</button>
```

Replace target with a div that shows hunting status/companies/candidates.

**Validation:** Button visible on all jobs. Click triggers route. Loading state shows while agent runs.

## Task 3: Create hunting UI templates

**Files:** templates/jobs/hunting-companies.html, templates/jobs/hunting-candidates.html

**Action:**

1. **hunting-companies.html** (extends base.html):
   - Header: "Target Companies for {job.title}"
   - Subtitle: "{count} companies identified | {hunting_session.status}"
   - List of company cards (stacked vertical, gap-4):
     - Card layout: white bg, border-gray-200, p-4, rounded
     - Content: name (font-semibold) | industry (text-sm gray) | size (text-sm gray) | LinkedIn link (icon + link, blue-600)
     - Actions: "View on LinkedIn" (external link icon) | "Remove" (trash icon, red on hover)
   - Empty state: "No companies yet. Click 'Start Hunting' to begin."
   - Optional "Add Company Manually" button (for Phase 2.2+)
   - Below companies: candidate cards section or "Searching for candidates..." status

2. **hunting-candidates.html** (included in hunting page or standalone):
   - Header: "Candidates for {job.title}"
   - Filter tabs (optional): "All" | "Approved" | "Rejected" (use JS tab toggle or separate routes)
   - Candidate card grid (grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-4):
     - Card layout: white bg, border-gray-200, p-4, rounded
     - Header row: candidate name (font-semibold) | status badge (badge-{status} class, top right)
     - Content: current title (text-sm gray) | current company (text-sm gray) | LinkedIn link (blue-600) | email (gray-700 or "Not available")
     - Actions (flex row, gap-2): "Edit" (btn-secondary, small) | "Approve & Proceed" (btn-primary) | "Skip" (btn-secondary)
   - Empty state: "No candidates found. The AI is searching... Refresh to check progress."
   - Approve/Skip buttons use HTMX POST: `hx-post="/hunting/{session_id}/candidates/{id}/approve"` etc.

**Styling notes:**
- Use Tailwind CDN classes (inherited from Phase 1)
- Status badges: Apply semantic colors from CSS classes (hunting=cyan-100/cyan-900, approved=green-100/green-900, etc.)
- HTMX loading state: Add `hx-confirm` for destructive actions (Skip, Remove)
- Card hover: Add shadow-md on hover (Tailwind shadow utilities)

## Task 4: Implement RoleIdentifierAgent

**Files:** src/app/agents/role_identifier.py

**Action:** Create the agent that discovers candidates at target companies.

1. **RoleIdentifierRequest Pydantic model:**
   - job_title: str
   - job_description: str
   - seniority: str (from job.seniority)
   - target_companies: list[TargetCompanyItem] (name, industry, size)

2. **RoleIdentifierResponse Pydantic model:**
   - candidates: list[CandidateItem]
   - CandidateItem: name, current_title, current_company, email (optional), linkedin_url (optional)

3. **RoleIdentifierAgent(BaseAgent):**
   - `system_prompt()`: Instruct Claude to identify 3-5 candidates per company matching the role seniority and company context
   - `tools()`: Define tool `identify_candidates_at_company` with fields: candidate_name, current_title, current_company, email, linkedin_url
   - `parse_response()`: Extract tool calls, return CandidateItem list
   - `async def run(request: RoleIdentifierRequest) -> AgentResponse`: Call parent.run(), return response

4. **Mock data fallback:** Hardcoded realistic candidates (with comment: `# MOCK DATA`) if API fails. Include variety of match levels.

5. **Integration with hunting route:** In start_hunting route, after CompanyMapperAgent completes:
   - For each TargetCompany created, queue RoleIdentifierAgent.run() via BackgroundTasks
   - RoleIdentifierAgent creates Candidate records with status="hunting"

## Task 5: Update job detail template to navigate to hunting

**Files:** templates/jobs/detail.html

**Action:** Modify the job detail template:

1. Add "Start Hunting" button to the sidebar actions div:
```html
<button hx-post="/jobs/{{ job.id }}/hunting/start"
        hx-target="body"
        class="btn-primary w-full mb-3">
  Start Hunting
</button>
```

2. After existing "Edit Job" and "Archive Job" buttons.

3. Below actions, add a status indicator: "Hunting status: {latest_session.status}" (if session exists).

**Validation:** Button visible. Click works. Loads hunting page.

## Task 6: Add Phase 2 status badge CSS

**Files:** static/style.css

**Action:** Add semantic color classes for Phase 2 status badges:

```css
/* Phase 2 status badges */
.badge-hunting {
    @apply bg-cyan-100 text-cyan-900;
}
.badge-approved {
    @apply bg-green-100 text-green-900;
}
.badge-rejected {
    @apply bg-red-100 text-red-900;
}
.badge-pending-outreach {
    @apply bg-amber-100 text-amber-900;
}
.badge-sent {
    @apply bg-purple-100 text-purple-900;
}
.badge-replied {
    @apply bg-emerald-100 text-emerald-900;
}
.badge-not-interested {
    @apply bg-gray-100 text-gray-900;
}
```

**Validation:** Badge CSS uses Tailwind utilities. Colors match UI-SPEC.md semantic palette.

## Task 7: Write integration tests for hunting routes

**Files:** tests/test_hunting_routes.py

**Action:** Add comprehensive tests for hunting workflow:

1. **Test start_hunting route:**
   - POST to /jobs/{job_id}/hunting/start
   - Verify HuntingSession created with status="pending"
   - Verify CompanyMapperAgent is queued (mock BackgroundTasks)
   - Verify redirect response

2. **Test get_companies route:**
   - GET /jobs/{job_id}/hunting/companies
   - Verify HTML fragment returned
   - Verify company cards rendered with all fields
   - Verify empty state shown if no companies

3. **Test get_candidates route:**
   - GET /jobs/{job_id}/hunting/candidates
   - Verify candidate cards rendered
   - Verify status badges applied correctly
   - Verify actions (approve/reject buttons) present

4. **Test approve_candidate route:**
   - POST to /hunting/{session_id}/candidates/{id}/approve
   - Verify Candidate.status changed to "approved"
   - Verify 200 response

5. **Test reject_candidate route:**
   - POST to /hunting/{session_id}/candidates/{id}/reject
   - Verify Candidate.status changed to "rejected"
   - Verify 200 response

6. **Test error cases:**
   - Job not found: 404
   - Session not found: 404
   - Candidate not found: 404

**Use fixtures from conftest.py:** job_data, hunting_session_fixture, target_companies_fixture, candidates_fixture

**Verification:** `pytest -xvs tests/test_hunting_routes.py --tb=short`

</tasks>

<verification>

### Automated Tests
```
pytest -xvs tests/test_hunting_routes.py -k "start_hunting" --tb=short
pytest -xvs tests/test_hunting_routes.py -k "approve_candidate" --tb=short
pytest -xvs tests/test_hunting_routes.py -k "list_companies" --tb=short
```

### Manual Verification (requires app running)
1. Start app: `uv run uvicorn src.app.main:app --reload`
2. Create a job via UI: http://localhost:8000/jobs/create
3. Navigate to job detail: http://localhost:8000/jobs/1
4. Click "Start Hunting" button
5. Observe:
   - Page redirects to hunting view
   - Company cards appear (with mock data or real API response)
   - Candidate cards appear below
   - Approve/Reject buttons work
   - Status badges render with correct colors
6. Click "Approve & Proceed" on a candidate → status changes to "approved"
7. Click "Skip" on a candidate → status changes to "rejected"

### Expected Output
```
tests/test_hunting_routes.py::test_start_hunting_creates_session PASSED
tests/test_hunting_routes.py::test_get_companies_returns_cards PASSED
tests/test_hunting_routes.py::test_approve_candidate_updates_status PASSED
tests/test_hunting_routes.py::test_reject_candidate_updates_status PASSED
tests/test_hunting_routes.py::test_error_handling_not_found PASSED
```

### Visual Verification
- "Start Hunting" button visible on job detail sidebar (primary blue)
- Clicking button shows loading spinner ("Hunting...")
- Company list appears with name, industry, size, LinkedIn link
- Candidate cards display with status badges (cyan for hunting)
- Approve button changes status to "approved" (green badge)
- Reject button changes status to "rejected" (red badge)

</verification>

<success_criteria>

- /jobs/{id}/hunting/start route creates HuntingSession and queues CompanyMapperAgent
- /jobs/{id}/hunting displays companies and candidates from database
- Company cards render with all fields (name, industry, size, LinkedIn URL)
- Candidate cards render with all fields (name, title, company, email, LinkedIn, status badge)
- Approve candidate route updates status to "approved" and renders green badge
- Reject candidate route updates status to "rejected" and renders red badge
- "Start Hunting" button visible on job detail page and functional
- All tests pass: `pytest -xvs tests/test_hunting_routes.py`
- Status badge CSS classes applied correctly (cyan, green, red per semantic palette)
- HTMX interactions work (POST buttons, response rendering)
- Hunting detail page accessible at /jobs/{id}/hunting and displays current session
- RoleIdentifierAgent integrated with BackgroundTasks to discover candidates
- All templates inherit from base.html and use Tailwind CDN classes (no new build steps)

</success_criteria>

<output>
After completion, create `.planning/phases/02-hunting-outreach-ai-candidate-discovery/02-PLAN-SUMMARY.md` with:
- What was built (routes, agents, templates, tests)
- Verification results (test output, manual testing screenshots/notes)
- Files created/modified
- Commits made
- Next steps (Plan 03 depends on approved candidates from this plan)
</output>
