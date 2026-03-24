# Roadmap: HR Recruitment AI Platform

**Created:** 2026-03-23
**Model:** Coarse granularity — 4 phases, ship something usable after each one.

---

## Phase 1: Foundation — Job & Project Setup
**Goal:** Consultant can create a job, define the search scope, and have everything stored correctly for the AI agents to work from.

**Requirements covered:** JOB-01, JOB-02, JOB-03, JOB-04

**Plans:** 2 plans in 2 waves

### Plan 01 — Project scaffold & SQLModel data models ✓ COMPLETE
- ✅ Python project structure with uv (FastAPI + SQLite)
- ✅ SQLModel data models for Client and Job with all JOB-01, JOB-02, JOB-03, JOB-04 fields
- ✅ Database layer with SQLAlchemy engine and session management
- ✅ Database initialization via FastAPI lifespan event
- ✅ Test infrastructure with pytest fixtures and conftest
- ✅ 6 tasks, 11 files created, 6 commits
- ✅ Summary: .planning/phases/01-foundation-job-project-setup/01-PLAN-SUMMARY.md

### Plan 02 — Job management API routes and UI ✓ COMPLETE
- ✅ FastAPI routes for job CRUD (create, list, detail, archive)
- ✅ Jinja2 templates with Tailwind CSS and HTMX for interactive UI
- ✅ Job creation form with all required fields
- ✅ Job dashboard with status badges
- ✅ Job detail view and edit form
- ✅ Archive action with HTMX POST request

**Verification:** Consultant can create a real job for a real client, define target industries, and see it in the dashboard. Job can be archived via UI button.

---

## Phase 2: Hunting & Outreach — AI Candidate Discovery
**Goal:** Given a job, AI identifies target companies, finds the right people, and drafts personalized outreach. Consultant reviews and approves before anything is sent.

**Requirements covered:** HUNT-01, HUNT-02, HUNT-03, HUNT-04, OUTR-01, OUTR-02, OUTR-03, OUTR-04

**Plans:** 3 plans in 3 waves

### Plan 01 — Data models & AI agent infrastructure
- Database models: HuntingSession, TargetCompany, Candidate, OutreachDraft
- Status enums: HuntingStatus, CandidateStatus, OutreachStatus
- Anthropic SDK integration (claude-haiku-4-5 for cost efficiency)
- BaseAgent abstract class pattern (reusable for all agents)
- CompanyMapperAgent implementation (generates target companies)
- Test infrastructure for agent testing
- 6 tasks, creates src/app/agents/ module, updates pyproject.toml with anthropic SDK

### Plan 02 — Company mapping + role identification UI
- FastAPI routes for hunting workflows: start session, list companies, approve/reject candidates
- RoleIdentifierAgent (discovers candidates at target companies)
- Jinja2 templates: hunting-companies.html, hunting-candidates.html
- "Start Hunting" button on job detail (primary blue)
- Company cards: name, industry, size, LinkedIn URL with remove action
- Candidate cards: name, title, company, email, LinkedIn, status badge with approve/reject
- Status badges CSS (cyan=hunting, green=approved, red=rejected)
- HTMX integration for async updates
- Integration tests for routes and agent

### Plan 03 — Outreach drafting agent + approval flow
- OutreachDrafterAgent (generates LinkedIn message + email per candidate)
- FastAPI routes: generate drafts, list/edit/approve/discard drafts, queue for sending
- Jinja2 templates: outreach-drafts.html (draft review with tabs and edit), outreach-queue.html (status tracking)
- Edit mode: inline textarea for message customization
- Approval flow: "Approve & Queue" button (green), status tracking
- Batch sending queue (marks approved as sent)
- Status tracking: pending_review → approved → sent → replied/not_interested
- Outreach timeline with timestamps per candidate
- Integration tests for agent and routes

**Verification:** Consultant runs a real hunting session for a job, reviews AI-generated candidates and outreach drafts, and marks at least one batch as ready to send.

---

## Phase 3: Classification & Client Presentation
**Goal:** Candidate profiles are scored automatically, classified with the correct tags, and exported cleanly for client review.

**Requirements covered:** CAND-01 through CAND-05, PRES-01, PRES-02, PRES-03

### Plans

**3.1 — Candidate profile ingestion**
- Consultant can manually add candidates or paste CV / LinkedIn URL
- AI parses profile into structured fields: experience, current role, company, salary expectation, skills
- Handles both direct upload and copy-paste text

**3.2 — AI classification agent**
- AI scores candidate against JD on: experience match, role relevance, salary alignment, seniority
- Auto-assigns tag: Sí / Evaluar / No interesa / No perfil / Sueldo with reasoning
- Consultant can override with single click

**3.3 — Client presentation export**
- Filter view: show only `Sí` + `Evaluar` candidates
- Export to Excel (with structured columns) and PDF (presentation format)
- Consultant marks which candidates the client approves for interview

**Verification:** Full pipeline from candidate entry → AI classification → export runs cleanly on a real job. Client-facing export looks professional.

---

## Phase 4: Interview Informe & Notifications
**Goal:** After interviews, AI generates the structured informe report and WhatsApp notifications keep the consultant informed without switching contexts.

**Requirements covered:** INTV-01 through INTV-04, NOTF-01, NOTF-02

### Plans

**4.1 — Interview informe agent**
- Consultant pastes interview transcript or structured notes
- AI generates informe: candidate summary, key strengths, concerns, fit-vs-JD analysis, recommendation
- Informe exported as PDF in clean presentation format
- Reference check log attached to candidate profile

**4.2 — WhatsApp notifications**
- Integration with WhatsApp Business API (or Twilio)
- Notification triggers: candidate replies to outreach, shortlist ready, interview report generated
- Consultant can reply to notifications to update candidate status

**Verification:** Full end-to-end run on a real active job: hunt → classify → export → interview → informe generated. Consultant receives WhatsApp notification at key steps.

---

## Milestone: v1 Complete ✓

At the end of Phase 4, the consultant can:
1. Create a job and define the search scope
2. Get an AI-generated list of candidates from target companies
3. Review and approve personalized outreach drafts
4. Score and classify candidates automatically
5. Export a clean shortlist for the client
6. Paste an interview transcript and get a professional informe
7. Receive WhatsApp notifications at key steps

This is a deployable, sellable product for the first client.

---

## Phase 5+ (Post-v1)

- Client portal with read-only shortlist view
- AI-driven follow-up scheduling
- Analytics dashboard (time-to-fill, conversion rates)
- Multi-client / multi-consultant support
- Automated LinkedIn outreach (pending ToS strategy)

---

*Roadmap created: 2026-03-23*
*Last updated: 2026-03-24 — Phase 2 plans created*
