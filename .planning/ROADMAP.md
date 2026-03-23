# Roadmap: HR Recruitment AI Platform

**Created:** 2026-03-23
**Model:** Coarse granularity — 4 phases, ship something usable after each one.

---

## Phase 1 — Foundation: Job & Project Setup
**Goal:** Consultant can create a job, define the search scope, and have everything stored correctly for the AI agents to work from.

**Requirements covered:** JOB-01, JOB-02, JOB-03, JOB-04

### Plans

**1.1 — Project scaffold & data models**
- Python project structure (FastAPI + SQLite/PostgreSQL)
- Data models: Job, Company, Candidate, OutreachMessage, InterviewNote
- Basic CLI or web scaffold to verify models work

**1.2 — Job management UI**
- Create/edit/archive job form
- Target industry + company type definition (free text + tags)
- Job list dashboard with status per job (Hunting / Shortlisting / Interviewing / Closed)

**Verification:** Consultant can create a real job for a real client, define target industries, and see it in the dashboard.

---

## Phase 2 — Hunting & Outreach: AI Candidate Discovery
**Goal:** Given a job, AI identifies target companies, finds the right people, and drafts personalized outreach. Consultant reviews and approves before anything is sent.

**Requirements covered:** HUNT-01, HUNT-02, HUNT-03, HUNT-04, OUTR-01, OUTR-02, OUTR-03, OUTR-04

### Plans

**2.1 — Company mapping agent**
- AI agent: given industry + company-type criteria, generate a list of target companies
- Output: company name, industry, size, LinkedIn company URL
- Consultant can add, remove, or adjust the list

**2.2 — Role identification agent**
- AI agent: for each target company, identify who holds the target role and similar titles
- Enrich with: name, current title, LinkedIn URL, email (where findable via public sources)
- Output shown as candidate cards for consultant review

**2.3 — Outreach drafting agent**
- AI agent: for each approved candidate, draft a LinkedIn message + email
- Drafts grounded in the JD — personalized to candidate's current role and company
- Consultant approval flow: approve / edit / reject per candidate
- System tracks outreach status: pending → sent → replied / not interested

**Verification:** Consultant runs a real hunting session for a job, reviews AI-generated candidates and outreach drafts, and marks at least one batch as ready to send.

---

## Phase 3 — Classification & Client Presentation
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

## Phase 4 — Interview Informe & Notifications
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
