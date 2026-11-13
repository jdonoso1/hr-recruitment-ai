# Phase 02 Plan 03 — Outreach Drafting & Approval Flow: Summary

**Status:** ✓ COMPLETE (2026-11-13)
**Requirements:** OUTR-01, OUTR-02, OUTR-03, OUTR-04

## What was built

- **OutreachDrafterAgent** (`src/app/agents/outreach_drafter.py`) — one Claude tool call per
  approved candidate returns a LinkedIn message (≤1000 chars) and an email with a subject line
  (≤2000 chars), grounded in job title/seniority/description/salary and the candidate's
  role/company. Over-long output is trimmed with a visible `[Trimmed — too long]` note.
- **Template fallback** — when `ANTHROPIC_API_KEY` is unset or a call fails, a plain draft is
  built from the real job/candidate data and labelled `[Template draft — ...]`. No invented
  "mock" content reaches a candidate-facing draft.
- **Routes** (`src/app/routes/outreach.py`):
  - `POST /outreach/generate` — background drafting (concurrent agent calls) for approved
    candidates without an active draft; redirects to the drafts page, which polls until done.
  - `GET /jobs/{id}/outreach/drafts` (+ `/list` fragment) — filter tabs: All / Pending / Approved / Sent.
  - `POST /outreach/{id}/edit|approve|discard` — HTMX card swaps; 400 on empty/over-long, 409 on
    invalid status transitions.
  - `GET /jobs/{id}/outreach/queue`, `POST /outreach/queue/send` (scoped to one job),
    `POST /outreach/{id}/status` (sent → replied / not_interested).
- **Templates** — `outreach-drafts.html`, `outreach-drafts-list.html`, `outreach-draft-card.html`,
  `outreach-queue.html`, `outreach-queue-card.html`; job detail sidebar gains
  "Generate Outreach (N)", "View Outreach Drafts", "Outreach Queue".
- **Tests** — `tests/test_outreach_agent.py` (17), `tests/test_outreach_routes.py` (36). API always mocked.

## Deviations from the plan

- **New `OutreachStatus.discarded`** instead of reusing `error` for discards, so `error` keeps
  meaning "send failed". Stored as text in SQLite; no schema change needed.
- **Generate redirects** to the drafts page (form POST) instead of returning JSON — the plan's
  `hx-vals` snippet was invalid JSON and a redirect fits the UI flow better.
- **Edit/approve return the re-rendered card** (not empty) so the badge updates in place.
- **Drafts are editable only while `pending_review`**; approval means the content is final.
- **No `approved_at` / `replied_at` columns** — adding columns would break existing local SQLite
  DBs (no migrations for the app module). The timeline uses `updated_at` for the latest step.
- **No "Retry" action** — nothing sets `error` until real sending exists.

## Fixes along the way

- Timezone-aware `utcnow()` helper: newer SQLModel rejects naive datetimes (23 tests were failing).
- `base.html` component styles now use `<style type="text/tailwindcss">`; previously `@apply` in a
  plain `<style>` was ignored, so `.btn-primary` etc. rendered unstyled.
- `[hidden] { display: none !important }` so utility classes like `.flex` can't unhide elements.
- Global `htmx:responseError` handler shows server error details (e.g. validation) in an alert.

## Verification

- `pytest`: 104 passed (51 pre-existing + 53 new).
- Browser run (Playwright, template-draft mode): generate → poll → edit → approve → discard →
  queue → send → mark replied; no console errors; checked desktop and 390px mobile.

## Phase 2 — what the system can now do

Job → AI target companies → AI candidates → consultant approves candidates → AI outreach drafts →
consultant edits/approves → queue → mark sent → track replied / not interested.

## Known gaps / next steps

- Sending is a placeholder (marks as sent); real LinkedIn/email delivery is not integrated.
- Header counts on the drafts page refresh on reload, not after each in-place HTMX action.
- Phase 3 (Classification & Client Presentation) builds on sent/replied candidates; the merged
  `src/hr_platform` screening/presentation agents are candidates for reuse there.
