---
phase: 02-hunting-outreach-ai-candidate-discovery
plan: 03
type: execute
wave: 3
depends_on: [01, 02]
files_modified:
  - src/app/agents/outreach_drafter.py
  - src/app/routes/outreach.py
  - src/app/routes/jobs.py
  - templates/jobs/outreach-drafts.html
  - templates/jobs/outreach-queue.html
  - tests/test_outreach_routes.py
  - tests/test_outreach_agent.py
autonomous: true
requirements: [OUTR-01, OUTR-02, OUTR-03, OUTR-04]
user_setup: []

must_haves:
  truths:
    - "Approved candidates have outreach drafts generated (LinkedIn message + email) grounded in job context"
    - "Consultant can view, edit, and approve outreach drafts for each candidate"
    - "Outreach status transitions: pending_review → approved → sent → replied/not_interested"
    - "Consultant can queue approved drafts for sending (when actual API integration available)"
    - "Outreach history shows creation, approval, sending, and reply timestamps"
  artifacts:
    - path: "src/app/agents/outreach_drafter.py"
      provides: "OutreachDrafterAgent that generates LinkedIn message and email per approved candidate"
      exports: ["OutreachDrafterAgent", "OutreachDrafterRequest", "OutreachDrafterResponse"]
      min_lines: 120
    - path: "src/app/routes/outreach.py"
      provides: "FastAPI routes for outreach drafting: create_drafts, list_drafts, approve_draft, discard_draft, queue_for_sending"
      exports: ["router"]
      min_lines: 250
    - path: "templates/jobs/outreach-drafts.html"
      provides: "Outreach draft review template with LinkedIn/Email tabs, inline editing, approve/discard buttons"
      min_lines: 120
    - path: "templates/jobs/outreach-queue.html"
      provides: "Outreach queue/status dashboard showing approved drafts ready to send and sent messages"
      min_lines: 100
    - path: "tests/test_outreach_routes.py"
      provides: "Integration tests for outreach routes: create, list, approve, discard, queue"
      min_lines: 150
    - path: "tests/test_outreach_agent.py"
      provides: "Unit/integration tests for OutreachDrafterAgent message generation"
      min_lines: 100
  key_links:
    - from: "src/app/routes/outreach.py"
      to: "src/app/agents/outreach_drafter.py"
      via: "create_drafts route calls OutreachDrafterAgent.run() for each approved candidate"
      pattern: "OutreachDrafterAgent.*run"
    - from: "src/app/agents/outreach_drafter.py"
      to: "src/app/models.py"
      via: "Agent generates OutreachDrafterResponse, stored as OutreachDraft records with status=pending_review"
      pattern: "OutreachDraft.*pending_review"
    - from: "templates/jobs/outreach-drafts.html"
      to: "src/app/routes/outreach.py"
      via: "Approve/Discard buttons POST to /outreach/{draft_id}/approve|discard"
      pattern: "hx-post.*outreach.*approve"
    - from: "src/app/routes/jobs.py"
      to: "src/app/routes/outreach.py"
      via: "Job detail sidebar has 'Generate Outreach' button that navigates to outreach drafting flow"
      pattern: "jobs.*outreach"

---

<objective>
Complete the Phase 2 hunting & outreach workflow by adding outreach draft generation, consultant approval flow, and status tracking. This plan creates: (1) OutreachDrafterAgent that generates personalized LinkedIn messages and emails grounded in job context, (2) FastAPI routes for draft management and approval flow, (3) templates for reviewing and editing drafts, and (4) tests for the complete workflow.

Purpose: This is the final step of Phase 2. After hunting yields approved candidates (Plan 02), this plan generates customized outreach messages that the consultant reviews, approves, and queues for sending. The system tracks each outreach's status (pending → approved → sent → replied) end-to-end.

Output: Fully functional outreach drafting and approval workflow with message generation, consultant review, and status tracking.
</objective>

<context>
From Plans 01-02 (this phase):
- HuntingSession, TargetCompany, Candidate, OutreachDraft models created
- CompanyMapperAgent and RoleIdentifierAgent working
- Consultant can start hunting and approve candidates
- Approved candidates awaiting outreach drafting

Phase 2 UI contract (from UI-SPEC.md):
- "Generate Outreach" button on hunting page (initiates drafting for approved candidates)
- Outreach draft cards: two tabs (LinkedIn Message | Email), read/edit mode toggle
- Approval flow: "Approve & Queue" button (green), "Discard" button
- Status tracking: pending_review (amber) → approved (green) → sent (purple) → replied (emerald) / not_interested (gray)
- Edit mode: Textarea for each message, "Save Edits" button, validates before storage

Key patterns:
- OutreachDraft.linkedin_message and OutreachDraft.email_message are TEXT columns (10,000 chars max)
- OutreachStatus enum: pending_review, approved, sent, replied, not_interested, error
- Message personalization: Ground drafts in job.description, job.seniority, candidate.current_title, candidate.current_company
- Consultant can edit drafts before approving (to customize tone, add context, etc.)
</context>

<tasks>

## Task 1: Implement OutreachDrafterAgent

**Files:** src/app/agents/outreach_drafter.py

**Action:** Create the agent that generates personalized outreach messages.

1. **OutreachDrafterRequest Pydantic model:**
   - job: JobSummary (id, title, description, seniority, salary_min, salary_max, required_experience_years)
   - candidate: CandidateSummary (name, current_title, current_company, linkedin_url)
   - company: TargetCompanySummary (name, industry, size_description)

2. **OutreachDrafterResponse Pydantic model:**
   - linkedin_message: str (max 1000 chars, first message in thread)
   - email_message: str (max 2000 chars, formal email)

3. **OutreachDrafterAgent(BaseAgent):**
   - `system_prompt()`: Instruct Claude to draft a personalized LinkedIn message (professional, brief, mention job match) and an email (formal, detailed, include job context). Messages should:
     - Reference candidate's current role/company (show you did research)
     - Mention specific job details (seniority, industry match)
     - Include soft CTA: "interested?" or "open to exploring?" (not pushy)
     - Be suitable for initial outreach (not follow-up)
   - `tools()`: Define tool `generate_outreach_messages` with fields: linkedin_message, email_message, both with type string
   - `parse_response()`: Extract tool call, validate against OutreachDrafterResponse schema, return
   - `async def run(request: OutreachDrafterRequest) -> AgentResponse`: Call parent.run()

4. **Mock data fallback:** Hardcoded realistic LinkedIn/email messages (clearly marked as MOCK) if API fails.

5. **Validation:** linkedin_message ≤ 1000 chars, email_message ≤ 2000 chars. If longer, truncate with note "[Trimmed — too long]" and log warning.

## Task 2: Create outreach routes module

**Files:** src/app/routes/outreach.py

**Action:** Create new router with outreach draft management endpoints:

1. **POST /outreach/generate**
   - Trigger OutreachDrafterAgent for all approved candidates in a hunting session
   - Request body: `{ job_id: int, hunting_session_id: int }`
   - For each Candidate with status="approved":
     - Call OutreachDrafterAgent.run() with candidate + job context
     - Create OutreachDraft record with status="pending_review", linkedin_message, email_message
     - Queue via BackgroundTasks (don't block response)
   - Return JSON: `{ message: "Generating drafts for N candidates...", session_id: int, draft_count: int }`

2. **GET /jobs/{job_id}/outreach/drafts**
   - Render outreach drafts page (template: outreach-drafts.html)
   - Query all OutreachDraft records for this job (with related candidate, company, job data)
   - Filter tabs (optional): "All" | "Pending Review" | "Approved" | "Sent"
   - Pass to template: job, drafts (with related data), counts

3. **GET /jobs/{job_id}/outreach/queue**
   - Render outreach queue/status page (template: outreach-queue.html)
   - Query OutreachDraft records with status in ["approved", "sent", "replied", "error"]
   - Show status timeline per candidate
   - Show CTA for batch sending (if approved count > 0)

4. **POST /outreach/{draft_id}/approve**
   - Update OutreachDraft.status = "approved"
   - Return empty response (HTMX removes/hides the draft card)

5. **POST /outreach/{draft_id}/discard**
   - Update OutreachDraft.status = "error" (or soft delete flag)
   - Return empty response

6. **POST /outreach/{draft_id}/edit**
   - Request body: `{ linkedin_message: string, email_message: string }`
   - Update OutreachDraft.linkedin_message, OutreachDraft.email_message
   - Validate lengths (≤1000 and ≤2000 respectively)
   - Return JSON: `{ success: bool, error: string | null, draft: OutreachDraft }`

7. **POST /outreach/queue/send**
   - Batch action: Queue all approved drafts for sending (when real API available)
   - For now: Update all approved drafts to status="sent", set sent_at timestamp
   - Return redirect to queue page with success message
   - Note in code: "PLACEHOLDER — when Twilio/LinkedIn API integrated, actual sending happens here"

**Integration with Phase 1/2:**
- Add outreach router to main.py: `app.include_router(outreach.router)`
- Link from job detail: Add "Generate Outreach" button (visible if candidates approved)

## Task 3: Create outreach draft templates

**Files:** templates/jobs/outreach-drafts.html, templates/jobs/outreach-queue.html

**Action:**

1. **outreach-drafts.html** (extends base.html):
   - Header: "Outreach Drafts for {job.title}"
   - Subtitle: "{count} drafts | {pending_count} pending review"
   - Filter tabs (optional, Phase 2.1): "All" | "Pending Review" | "Approved" | "Sent"
   - Draft cards stacked vertical, gap-6:
     - Card layout: white bg, border-gray-200, p-6, rounded
     - Header row: Candidate name (font-semibold) | Status badge (top right, badge-{status})
     - Tab switcher: "LinkedIn Message" | "Email" (CSS tabs or JavaScript toggle)
     - Read mode: Message displayed in gray bg (bg-gray-50), p-4, border-radius, pre-wrap
     - Edit mode: Textarea with form-input class, height 200px, validates on save
     - Edit toggle button: Pencil icon, secondary gray
     - Action buttons (bottom row, flex, gap-3):
       - "Save Edits" button (appears only in edit mode, primary blue)
       - "Approve & Queue" button (primary green, #16A34A)
       - "Discard" button (secondary gray)
     - HTMX: POST buttons use hx-post with hx-confirm for destructive (Discard)

2. **outreach-queue.html** (extends base.html):
   - Header: "Outreach Queue & Status for {job.title}"
   - Status dashboard: Cards per candidate showing:
     - Candidate name + current company
     - Status badge (pending, approved, sent, replied, error)
     - Timeline (created → approved → sent → replied) with timestamps
     - Last action: "Sent on Mar 24, 2026 at 2:30 PM" or "Replied Mar 25, 2026"
     - Inline actions: "Mark as Replied" (dropdown), "Retry" (if error)
   - Bottom CTA: "Send {approved_count} Approved Messages" button (only if approved_count > 0)
     - Uses hx-post to /outreach/queue/send with confirmation dialog
   - Empty state: "No approved drafts yet. Review drafts to approve."

**Styling notes:**
- Tab switcher: Use Tailwind border-b for active tab indicator
- Edit toggle: Pencil icon (Heroicons), secondary size
- Status badges: Use semantic colors (pending=amber, approved=green, sent=purple, replied=emerald, error=red)
- Timeline: Simple vertical line with dots per milestone (CSS border + circles)
- Card hover: Shadow increase on hover

## Task 4: Extend job detail to add "Generate Outreach" button

**Files:** src/app/routes/jobs.py, templates/jobs/detail.html

**Action:**

1. In job detail route: Query approved candidate count for latest hunting session
2. In template (detail.html): Add "Generate Outreach" button in sidebar (below "Start Hunting" if present):
```html
{% if approved_candidates_count > 0 %}
<button hx-post="/outreach/generate"
        hx-vals="{'job_id': {{ job.id }}, 'hunting_session_id': {{ hunting_session.id }}}"
        hx-target="body"
        class="btn-primary w-full mb-3">
  Generate Outreach ({{ approved_candidates_count }} candidates)
</button>
{% endif %}
```

3. Also add a link to view drafts/queue:
```html
{% if has_outreach_drafts %}
<a href="/jobs/{{ job.id }}/outreach/drafts" class="btn-secondary w-full text-center">
  View Outreach Drafts
</a>
{% endif %}
```

## Task 5: Write outreach agent tests

**Files:** tests/test_outreach_agent.py

**Action:** Test the OutreachDrafterAgent:

1. **Test agent initialization:** Verify AsyncClient created
2. **Test draft generation:**
   - Pass OutreachDrafterRequest with real job/candidate context
   - Verify response contains both linkedin_message and email_message
   - Verify messages are non-empty and under length limits
   - Verify personalization: messages mention candidate name, company, or role (use string search)
3. **Test message validation:**
   - Mock response with missing fields → verify Pydantic error
   - Mock response with overly long messages → verify truncation
4. **Test error handling:** Mock API error → verify AgentResponse.status="error"
5. **Test mock data fallback:** Use env var SKIP_API_TESTS=1, verify mock messages returned

**Verification:** `pytest -xvs tests/test_outreach_agent.py -k "outreach" --tb=short`

## Task 6: Write outreach routes integration tests

**Files:** tests/test_outreach_routes.py

**Action:** Test outreach route workflows:

1. **Test generate drafts route:**
   - POST to /outreach/generate with job_id and hunting_session_id
   - Verify OutreachDraft records created for each approved candidate
   - Verify drafts have status="pending_review"
   - Verify response includes draft count

2. **Test list drafts:**
   - GET /jobs/{job_id}/outreach/drafts
   - Verify HTML rendered with draft cards
   - Verify all drafts visible (approved, pending_review, sent)
   - Verify status badges applied

3. **Test approve draft:**
   - POST to /outreach/{draft_id}/approve
   - Verify OutreachDraft.status changed to "approved"
   - Verify 200 response

4. **Test discard draft:**
   - POST to /outreach/{draft_id}/discard
   - Verify OutreachDraft.status changed to "error"
   - Verify 200 response

5. **Test edit draft:**
   - POST to /outreach/{draft_id}/edit with new linkedin_message
   - Verify draft updated in database
   - Verify response includes success: true
   - Test with oversized message → verify error or truncation

6. **Test queue/send:**
   - POST to /outreach/queue/send (with mock approved drafts)
   - Verify all approved drafts updated to status="sent"
   - Verify sent_at timestamps set
   - Verify redirect to queue page

7. **Test error cases:**
   - Draft not found: 404
   - Job not found: 404
   - Invalid message length: 400 with error message

**Use fixtures:** job_data, hunting_session_fixture, candidates_fixture, outreach_drafts_fixture (create new)

**Verification:** `pytest -xvs tests/test_outreach_routes.py --tb=short`

## Task 7: Add Outreach integration to main.py and ensure models are imported

**Files:** src/app/main.py, src/app/models.py

**Action:**

1. In main.py:
   - Import outreach router: `from .routes import outreach`
   - Include in app: `app.include_router(outreach.router)`
   - Ensure OutreachDraft model is imported for table creation: `from .models import OutreachDraft`

2. Verify all models imported in main.py for lifespan initialization:
   ```python
   from .models import Client, Job, HuntingSession, TargetCompany, Candidate, OutreachDraft
   ```

3. Test database startup: `uv run uvicorn src.app.main:app --reload` should create all tables without errors

</tasks>

<verification>

### Automated Tests
```
pytest -xvs tests/test_outreach_agent.py --tb=short
pytest -xvs tests/test_outreach_routes.py --tb=short
```

### Manual Verification (requires app running)
1. Start app: `uv run uvicorn src.app.main:app --reload`
2. Complete hunting workflow:
   - Create job
   - Click "Start Hunting" → companies/candidates appear
   - Approve 2-3 candidates
3. On job detail, verify "Generate Outreach" button appears
4. Click "Generate Outreach" → navigate to /jobs/{id}/outreach/drafts
5. Observe:
   - Draft cards appear (one per approved candidate)
   - Status badges show "Pending Review" (amber)
   - LinkedIn Message and Email tabs both show draft text
   - Edit button toggles textarea
   - Approve button changes status to "Approved" (green badge)
   - Discard button removes draft
6. Navigate to /jobs/{id}/outreach/queue
   - Shows approved drafts with status timeline
   - "Send X Approved Messages" button visible
   - Click send → all drafts updated to "Sent" (purple badge)

### Expected Output
```
tests/test_outreach_agent.py::test_outreach_agent_generates_messages PASSED
tests/test_outreach_agent.py::test_messages_under_length_limits PASSED
tests/test_outreach_routes.py::test_generate_drafts_creates_records PASSED
tests/test_outreach_routes.py::test_approve_draft_updates_status PASSED
tests/test_outreach_routes.py::test_list_drafts_renders_cards PASSED
tests/test_outreach_routes.py::test_queue_send_updates_all_approved PASSED
```

### Visual Verification
- "Generate Outreach" button visible on job detail (only if candidates approved)
- Draft cards display with candidate name and status badge (amber)
- LinkedIn/Email tabs switch between messages
- Edit button shows textarea, "Save Edits" validates and saves
- Approve/Discard buttons work via HTMX
- Queue page shows timeline with status transitions
- "Send Messages" button updates all to purple badge (Sent)

</verification>

<success_criteria>

- OutreachDrafterAgent generates linkedin_message and email_message per approved candidate
- /outreach/generate route creates OutreachDraft records with status="pending_review"
- /jobs/{id}/outreach/drafts displays draft cards with edit, approve, discard actions
- Consultant can edit drafts inline and save changes
- Consultant can approve drafts (status → "approved", badge turns green)
- Consultant can discard drafts (status → "error", card hides)
- /jobs/{id}/outreach/queue shows approved drafts with timeline and "Send" CTA
- /outreach/queue/send batch-sends all approved (updates status to "sent", sets sent_at)
- All tests pass: `pytest -xvs tests/test_outreach_agent.py tests/test_outreach_routes.py`
- "Generate Outreach" button appears on job detail when candidates approved
- Status badges render with correct semantic colors (amber, green, purple, emerald, gray, red per UI-SPEC)
- All templates inherit from base.html, use Tailwind CDN (no new build step)
- Outreach workflow complete: approved candidates → drafts → consultant approval → queued for sending
- Error handling: invalid lengths, missing drafts, API failures all handled gracefully

</success_criteria>

<output>
After completion, create `.planning/phases/02-hunting-outreach-ai-candidate-discovery/03-PLAN-SUMMARY.md` with:
- What was built (agents, routes, templates, tests)
- Verification results (test output, manual testing)
- Files created/modified
- Commits made
- Complete Phase 2 summary: what hunting & outreach system can do
- Next steps: Phase 3 (Classification & Client Presentation) depends on approved/sent candidates from this phase

Also update `.planning/ROADMAP.md` to mark Phase 2 as complete and update Phase 2 Plans section:
```
### Plan 01 — Data models & AI agent infrastructure ✓ COMPLETE
- SQLModel tables: HuntingSession, TargetCompany, Candidate, OutreachDraft
- BaseAgent pattern, CompanyMapperAgent, Anthropic SDK integration
- Test infrastructure

### Plan 02 — Company mapping + role identification UI ✓ COMPLETE
- FastAPI routes for hunting workflow (start, list companies, approve candidates)
- RoleIdentifierAgent for candidate discovery
- Templates and HTMX interactions

### Plan 03 — Outreach drafting agent + approval flow ✓ COMPLETE
- OutreachDrafterAgent for message generation
- Outreach draft review and approval routes
- Status tracking (pending → approved → sent → replied)
- Batch sending queue
```
</output>
