# Requirements: HR Recruitment AI Platform

**Defined:** 2026-03-23
**Core Value:** AI does the hunting, outreach, and classification so the consultant only touches candidates worth their time.

## v1 Requirements

### Jobs

- [ ] **JOB-01**: Consultant can create a job with title, description, seniority level, salary range, and required experience
- [ ] **JOB-02**: Consultant can define target industries and company types for a job (e.g., "mass consumption", "tech startups")
- [ ] **JOB-03**: Consultant can view all active jobs in a dashboard with pipeline status
- [ ] **JOB-04**: Consultant can archive or close a job

### Hunting

- [ ] **HUNT-01**: AI generates a list of target companies given the industry/company-type criteria
- [ ] **HUNT-02**: AI identifies people holding the target role (and similar titles) at each target company
- [ ] **HUNT-03**: AI enriches each person with LinkedIn URL, current title, company, and email when findable
- [ ] **HUNT-04**: Consultant can review, edit, and approve the AI-generated candidate list before outreach

### Outreach

- [ ] **OUTR-01**: AI drafts a personalized LinkedIn message per candidate based on the JD
- [ ] **OUTR-02**: AI drafts a personalized email per candidate based on the JD
- [ ] **OUTR-03**: Consultant can approve, edit, or reject each draft before it is sent
- [ ] **OUTR-04**: System tracks outreach status per candidate (pending, sent, replied, not interested)

### Candidate Management

- [ ] **CAND-01**: Consultant can manually add a candidate with profile data (experience, role, company, salary expectation)
- [ ] **CAND-02**: Consultant can upload or paste a CV/LinkedIn profile for AI to parse into structured data
- [ ] **CAND-03**: AI scores candidate against JD and assigns classification: Sí / Evaluar / No interesa / No perfil / Sueldo
- [ ] **CAND-04**: Consultant can override AI classification with a manual tag
- [ ] **CAND-05**: Consultant can view all candidates per job filtered by classification

### Client Presentation

- [ ] **PRES-01**: System exports `Sí` + `Evaluar` candidates to a formatted Excel report
- [ ] **PRES-02**: System generates a PDF shortlist for sharing with the client
- [ ] **PRES-03**: Consultant can mark which candidates the client has approved for interview

### Interview & Informe

- [ ] **INTV-01**: Consultant can paste interview transcript or notes into the system per candidate
- [ ] **INTV-02**: AI generates a structured interview informe: profile summary, strengths, concerns, fit recommendation
- [ ] **INTV-03**: Informe is exportable as PDF in a clean presentation format
- [ ] **INTV-04**: Consultant can log reference check status and notes per candidate

### Notifications

- [ ] **NOTF-01**: WhatsApp notification when a candidate replies to outreach
- [ ] **NOTF-02**: WhatsApp notification when a job pipeline reaches a key milestone (e.g., shortlist ready)

## v2 Requirements

### Advanced Hunting

- **HUNT-05**: AI monitors LinkedIn for job changes at target companies and alerts consultant
- **HUNT-06**: AI scores company relevance automatically based on past successful placements

### Reporting & Analytics

- **REPT-01**: Dashboard shows time-to-fill metrics per job
- **REPT-02**: Conversion rates by classification tag over time
- **REPT-03**: Per-client placement history and revenue tracking

### Client Portal

- **CLNT-01**: Client gets a read-only link to view their shortlist and leave feedback
- **CLNT-02**: Client can mark candidates directly in the portal (no email back-and-forth)

### Automation

- **AUTO-01**: AI sends approved outreach messages automatically (requires LinkedIn API or manual workaround)
- **AUTO-02**: AI schedules follow-up messages if no reply after N days

## Out of Scope

| Feature | Reason |
|---------|--------|
| Video interview hosting | Use Zoom; link transcripts back manually |
| Automated LinkedIn sending without approval | LinkedIn ToS risk; consultant must send |
| Mobile app | Web + WhatsApp covers mobile access for v1 |
| Multi-user / team accounts | Single consultant for v1; team features in v2+ |
| Billing / subscription management | Handled outside platform for v1 |
| Job board posting | Not part of executive search workflow |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| JOB-01 | Phase 1 | Pending |
| JOB-02 | Phase 1 | Pending |
| JOB-03 | Phase 1 | Pending |
| JOB-04 | Phase 1 | Pending |
| HUNT-01 | Phase 2 | Pending |
| HUNT-02 | Phase 2 | Pending |
| HUNT-03 | Phase 2 | Pending |
| HUNT-04 | Phase 2 | Pending |
| OUTR-01 | Phase 2 | Pending |
| OUTR-02 | Phase 2 | Pending |
| OUTR-03 | Phase 2 | Pending |
| OUTR-04 | Phase 2 | Pending |
| CAND-01 | Phase 3 | Pending |
| CAND-02 | Phase 3 | Pending |
| CAND-03 | Phase 3 | Pending |
| CAND-04 | Phase 3 | Pending |
| CAND-05 | Phase 3 | Pending |
| PRES-01 | Phase 3 | Pending |
| PRES-02 | Phase 3 | Pending |
| PRES-03 | Phase 3 | Pending |
| INTV-01 | Phase 4 | Pending |
| INTV-02 | Phase 4 | Pending |
| INTV-03 | Phase 4 | Pending |
| INTV-04 | Phase 4 | Pending |
| NOTF-01 | Phase 4 | Pending |
| NOTF-02 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-23*
*Last updated: 2026-03-23 after initial questioning session*
