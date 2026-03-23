# HR Recruitment AI Platform

## What This Is

An AI-powered recruitment automation platform built for HR agencies and executive search consultants. It automates the full recruitment pipeline — from hunting and outreach to candidate classification and final interview reporting — so consultants can focus on relationships and judgment rather than manual research and data entry.

## Core Value

AI does the hunting, outreach, and classification so the consultant only touches candidates worth their time.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

**Job & Target Setup**
- [ ] Consultant creates a job with full JD (role, requirements, salary, seniority)
- [ ] Consultant defines target industries and company types (e.g., "mass consumption brands")
- [ ] System stores job context for AI agents to reference throughout the pipeline

**Hunting — AI Candidate Discovery**
- [ ] AI maps target companies in the specified industry/company-type scope
- [ ] AI identifies who holds the target role (and similar titles) at each company
- [ ] AI finds contact information: LinkedIn profile, email, phone when available
- [ ] Consultant reviews AI-generated candidate list before outreach begins

**Outreach — AI-Assisted Contact**
- [ ] AI drafts personalized LinkedIn messages and emails per candidate based on the JD
- [ ] Consultant approves or edits outreach before sending
- [ ] System tracks outreach status per candidate (sent, replied, not interested, etc.)

**Candidate Classification**
- [ ] Consultant logs candidate profile data (experience, current role, salary expectation)
- [ ] AI scores each candidate against the JD and assigns classification:
  - `Sí` — fully meets the profile
  - `Evaluar` — ~80% fit, worth considering
  - `No interesa` — candidate not interested
  - `No perfil` — does not meet requirements
  - `Sueldo` — salary mismatch
- [ ] Consultant can override AI classification with manual tag

**Client Presentation**
- [ ] System auto-exports `Sí` + `Evaluar` candidates to a formatted Excel/PDF report
- [ ] Client portal or shareable view shows shortlist for client feedback
- [ ] Client marks which candidates to advance to interview

**Interview & Reporting**
- [ ] Consultant can paste interview transcript or notes into system
- [ ] AI generates structured interview informe (candidate profile + strengths + concerns + recommendation)
- [ ] System tracks reference check status and stores reference notes
- [ ] Final report exported in presentation-ready format (PDF or Prezi-compatible)

**Dashboard & Tracking**
- [ ] Overview of all active jobs and pipeline stage per job
- [ ] Candidate count by classification per job
- [ ] WhatsApp integration for quick status updates and notifications

### Out of Scope

- Video interview hosting — use Zoom, link results back manually
- Automated sending of LinkedIn messages without consultant approval (legal/ToS risk)
- Mobile app — web-first, WhatsApp for lightweight mobile access
- Billing / subscription management — handled outside the platform for v1

## Context

- **First client:** The HR agency owner described their process via voice note. The owner IS the consultant — they do hunting, outreach, interviews, and reports themselves. The system must fit one person's workflow, not a large team.
- **Current workflow:** Manual LinkedIn hunting → phone/email outreach → data entered into a system → exported to Excel → sent to client → owner interviews shortlisted candidates → Prezi report created manually
- **Biggest time sinks:** Hunting (identifying who holds target roles at target companies) and creating the informe after each interview
- **Industry targeted first:** Executive search / headhunting for mid-to-senior roles (e.g., Marketing Manager at mass consumption companies)
- **Existing work:** A Python/FastAPI prototype exists at `/Ai Agency/projects/hr-platform` — rebuild from scratch with correct architecture
- **Revenue model:** One-time setup fee + monthly retainer per client (the agency)

## Constraints

- **Tech Stack:** Python — consistent with existing AI agency tooling and the owner's ecosystem
- **AI Provider:** Anthropic Claude via API — already in use across the agency
- **Interface:** Web dashboard (primary) + WhatsApp notifications (secondary)
- **Deployment:** Runs locally or on a VPS — no complex cloud infra for v1
- **Solo operator:** Platform must work well for a single consultant, not a team

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Rebuild rather than extend hr-platform | Existing prototype was exploratory; cleaner to start with correct architecture | — Pending |
| Web + WhatsApp (not mobile app) | Fastest path to usable product; WhatsApp already in the consultant's workflow | — Pending |
| Consultant approves outreach before sending | LinkedIn ToS + quality control; AI drafts, human sends | — Pending |

---
*Last updated: 2026-03-23 after initial questioning session*
