from __future__ import annotations

"""
HR Workflow Orchestrator
Sequences: ingest → screen → [recruiter review] → interview → enrich → present → persist
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .agents.enrichment import enrich_candidate
from .agents.interview import run_interview_stage
from .agents.presentation import generate_presentation
from .agents.screening import screen_all
from .db.database import (
    init_db,
    save_candidate,
    save_evaluation,
    save_interview,
    save_job,
    save_kpi,
)
from .ingestion.cv_parser import ingest_cv_file, ingest_linkedin_text
from .models.schema import (
    Candidate,
    HRWorkflowContext,
    Interview,
    Job,
    KPILog,
    RankedCandidate,
)

logger = logging.getLogger(__name__)

Observer = Callable[[str, str], None]  # (stage, message)


def _log(observer: Observer | None, stage: str, msg: str) -> None:
    logger.info("[%s] %s", stage, msg)
    if observer:
        observer(stage, msg)


# ─── Individual pipeline steps ────────────────────────────────────────────────

def step_ingest_cv(
    path: str,
    client_id: str,
    ctx: HRWorkflowContext,
    observer: Observer | None = None,
) -> Candidate:
    """Parse a CV file and add the candidate to the context."""
    _log(observer, "ingest", f"Parsing CV: {path}")
    candidate = Candidate(**ingest_cv_file(path, client_id))
    ctx.candidates.append(candidate)
    save_candidate(candidate)
    _log(observer, "ingest", f"Candidate ingested: {candidate.name}")
    return candidate


def step_ingest_linkedin(
    pasted_text: str,
    client_id: str,
    ctx: HRWorkflowContext,
    observer: Observer | None = None,
) -> Candidate:
    """Parse pasted LinkedIn profile text and add the candidate to the context."""
    _log(observer, "ingest", "Parsing LinkedIn profile")
    candidate = Candidate(**ingest_linkedin_text(pasted_text, client_id))
    ctx.candidates.append(candidate)
    save_candidate(candidate)
    _log(observer, "ingest", f"Candidate ingested: {candidate.name}")
    return candidate


def step_screen(
    ctx: HRWorkflowContext,
    observer: Observer | None = None,
) -> list[RankedCandidate]:
    """Screen all candidates against the job and rank them."""
    if not ctx.candidates:
        raise ValueError("No candidates to screen.")

    _log(observer, "screen", f"Screening {len(ctx.candidates)} candidate(s)...")
    ranked = screen_all(ctx.job, ctx.candidates)
    ctx.ranked = ranked

    for rc in ranked:
        rc.evaluation.stage = "screened"
        ctx.evaluations.append(rc.evaluation)
        save_evaluation(rc.evaluation)
        _log(observer, "screen", f"#{rc.rank} {rc.candidate.name} — score {rc.score:.1f}")

    return ranked


def step_interview(
    ctx: HRWorkflowContext,
    transcripts: dict[str, str] | None = None,
    observer: Observer | None = None,
) -> list[Interview]:
    """
    Run interview stage for all screened candidates.
    transcripts: mapping of candidate_id → transcript text (optional).
    If a transcript is provided, AI analysis is run automatically.
    """
    interviews: list[Interview] = []
    transcripts = transcripts or {}

    for rc in ctx.ranked:
        candidate = rc.candidate
        evaluation = rc.evaluation
        transcript = transcripts.get(candidate.candidate_id)

        _log(observer, "interview", f"Generating questions for {candidate.name}")
        interview = run_interview_stage(
            ctx.job, candidate, evaluation, transcript=transcript
        )
        ctx.interviews.append(interview)
        save_interview(interview)
        save_evaluation(evaluation)  # updated with interview scores if transcript provided

        interviews.append(interview)
        _log(observer, "interview", f"Interview stage done for {candidate.name}")

    return interviews


def step_enrich(
    ctx: HRWorkflowContext,
    observer: Observer | None = None,
) -> None:
    """Enrich all candidates with intelligence fields post-evaluation."""
    interview_map: dict[str, Interview] = {
        i.candidate_id: i for i in ctx.interviews
    }

    for rc in ctx.ranked:
        candidate = rc.candidate
        evaluation = rc.evaluation
        interview = interview_map.get(candidate.candidate_id)

        _log(observer, "enrich", f"Enriching {candidate.name}")
        enrich_candidate(candidate, evaluation, interview)
        save_candidate(candidate)

    _log(observer, "enrich", "All candidates enriched.")


def step_present(
    ctx: HRWorkflowContext,
    client_name: str,
    output_dir: str = ".",
    observer: Observer | None = None,
) -> str:
    """Generate a PowerPoint presentation and store the path in context."""
    _log(observer, "present", "Generating presentation...")
    interviews_map = {i.candidate_id: i for i in ctx.interviews}
    path = generate_presentation(
        ctx.job, client_name, ctx.ranked, interviews_map, output_dir
    )
    ctx.report_path = path
    _log(observer, "present", f"Presentation saved: {path}")
    return path


def step_kpi(
    ctx: HRWorkflowContext,
    observer: Observer | None = None,
) -> KPILog:
    """Compute and persist KPI metrics for this workflow run."""
    now = datetime.now(timezone.utc).isoformat()
    hired = sum(
        1 for rc in ctx.ranked
        if rc.evaluation.final_outcome == "hired"
    )
    reused = sum(1 for rc in ctx.ranked if rc.candidate.reusable)

    kpi = KPILog(
        client_id=ctx.job.client_id,
        job_id=ctx.job.job_id,
        period_start=ctx.job.created_at,
        period_end=now,
        candidates_processed=len(ctx.candidates),
        candidates_screened=len(ctx.ranked),
        candidates_interviewed=len(ctx.interviews),
        candidates_hired=hired,
        candidates_reused=reused,
        hours_saved_estimate=len(ctx.candidates) * 1.5,  # ~1.5 hrs saved per candidate
        reuse_rate_pct=(reused / len(ctx.candidates) * 100) if ctx.candidates else 0.0,
    )
    save_kpi(kpi)
    _log(observer, "kpi", f"KPI logged: {kpi.kpi_id}")
    return kpi


# ─── Full pipeline ─────────────────────────────────────────────────────────────

@dataclass
class WorkflowResult:
    ctx: HRWorkflowContext
    kpi: KPILog
    report_path: str | None = None
    errors: list[str] = field(default_factory=list)


def run_full_workflow(
    job: Job,
    cv_paths: list[str] | None = None,
    linkedin_profiles: list[str] | None = None,
    transcripts: dict[str, str] | None = None,
    client_name: str = "Client",
    output_dir: str = ".",
    observer: Observer | None = None,
    db_path: str | None = None,
) -> WorkflowResult:
    """
    Execute the complete HR pipeline:
    1. Init DB
    2. Save job
    3. Ingest CVs / LinkedIn profiles
    4. Screen & rank candidates
    5. Interview stage (questions + analysis if transcripts provided)
    6. Enrich candidate intelligence
    7. Generate presentation
    8. Log KPIs

    Parameters
    ----------
    job          : The Job to evaluate candidates against
    cv_paths     : List of PDF file paths
    linkedin_profiles : List of pasted LinkedIn profile texts
    transcripts  : {candidate_id: transcript_text} for completed interviews
    client_name  : Display name used in the presentation
    output_dir   : Directory where the .pptx file is saved
    observer     : Optional callback(stage, message) for progress tracking
    db_path      : Override DB path (useful for testing)
    """
    if db_path:
        import hr_platform.db.database as _db
        _db.DB_PATH = db_path

    init_db()
    save_job(job)

    ctx = HRWorkflowContext(job=job)
    errors: list[str] = []

    # ── Ingest ────────────────────────────────
    for path in (cv_paths or []):
        try:
            step_ingest_cv(path, job.client_id, ctx, observer)
        except Exception as exc:
            msg = f"Failed to ingest {path}: {exc}"
            errors.append(msg)
            _log(observer, "ingest_error", msg)

    for text in (linkedin_profiles or []):
        try:
            step_ingest_linkedin(text, job.client_id, ctx, observer)
        except Exception as exc:
            msg = f"Failed to ingest LinkedIn profile: {exc}"
            errors.append(msg)
            _log(observer, "ingest_error", msg)

    if not ctx.candidates:
        raise ValueError("No candidates ingested — cannot proceed.")

    # ── Screen ────────────────────────────────
    step_screen(ctx, observer)

    # ── Interview ─────────────────────────────
    step_interview(ctx, transcripts, observer)

    # ── Enrich ────────────────────────────────
    step_enrich(ctx, observer)

    # ── Present ───────────────────────────────
    try:
        report_path = step_present(ctx, client_name, output_dir, observer)
    except Exception as exc:
        msg = f"Presentation generation failed: {exc}"
        errors.append(msg)
        _log(observer, "present_error", msg)
        report_path = None

    # ── KPI ───────────────────────────────────
    kpi = step_kpi(ctx, observer)

    return WorkflowResult(ctx=ctx, kpi=kpi, report_path=report_path, errors=errors)
