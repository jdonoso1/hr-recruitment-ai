from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id() -> str:
    return str(uuid.uuid4())


# ─────────────────────────────────────────────
# CLIENT
# ─────────────────────────────────────────────

class Client(BaseModel):
    client_id: str = Field(default_factory=_id)
    name: str
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    plan: Literal["starter", "pro", "enterprise"] = "starter"
    active: bool = True
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)


# ─────────────────────────────────────────────
# JOB
# ─────────────────────────────────────────────

class Job(BaseModel):
    job_id: str = Field(default_factory=_id)
    client_id: str
    title: str
    company: str
    description: str
    required_skills: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    experience_min: int | None = None
    experience_max: int | None = None
    location: str | None = None
    remote_ok: bool = False
    salary_min: float | None = None
    salary_max: float | None = None
    status: Literal["open", "screening", "interviewing", "closed"] = "open"
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)


# ─────────────────────────────────────────────
# CANDIDATE
# ─────────────────────────────────────────────

class Candidate(BaseModel):
    candidate_id: str = Field(default_factory=_id)
    client_id: str

    # Identity
    name: str
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    location: str | None = None
    languages: list[str] = Field(default_factory=list)

    # Professional profile
    current_role: str | None = None
    current_company: str | None = None
    years_experience: float | None = None
    industries: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    cv_raw_text: str | None = None
    cv_file_path: str | None = None

    # Preferences
    salary_expectation: float | None = None
    salary_currency: str = "USD"
    relocation_ok: bool = False
    availability: str | None = None

    # Intelligence / reusability
    reusable: bool = True
    recommended_roles: list[str] = Field(default_factory=list)
    recommended_industries: list[str] = Field(default_factory=list)
    priority_level: Literal["low", "normal", "high"] = "normal"
    notes: str | None = None

    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)


# ─────────────────────────────────────────────
# SCREENING SCORE BREAKDOWN
# ─────────────────────────────────────────────

class ScoreBreakdown(BaseModel):
    overall: float = Field(ge=1, le=10)
    skills_match: float = Field(ge=1, le=10)
    experience_match: float = Field(ge=1, le=10)
    culture_fit: float = Field(ge=1, le=10)
    reasoning: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)


# ─────────────────────────────────────────────
# INTERVIEW ANALYSIS
# ─────────────────────────────────────────────

class InterviewAnalysis(BaseModel):
    overall_score: float = Field(ge=1, le=10)
    communication_score: float = Field(ge=1, le=10)
    technical_score: float = Field(ge=1, le=10)
    motivation_score: float = Field(ge=1, le=10)
    reasoning: str
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    recommended_questions: list[str] = Field(default_factory=list)  # follow-ups
    hire_recommendation: Literal["strong_yes", "yes", "neutral", "no", "strong_no"]


# ─────────────────────────────────────────────
# EVALUATION (candidate × job)
# ─────────────────────────────────────────────

EvaluationStage = Literal[
    "uploaded", "screened", "recruiter_review", "approved",
    "interview_scheduled", "interviewed", "evaluated",
    "report_generated", "hired", "rejected"
]

class Evaluation(BaseModel):
    evaluation_id: str = Field(default_factory=_id)
    candidate_id: str
    job_id: str
    client_id: str

    # Screening
    screening_score: float | None = None
    skills_score: float | None = None
    experience_score: float | None = None
    culture_score: float | None = None
    screening_reasoning: str | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)

    # Interview
    interview_score: float | None = None
    interview_notes: str | None = None
    interview_reasoning: str | None = None
    communication_score: float | None = None
    technical_score: float | None = None
    motivation_score: float | None = None

    # Workflow
    stage: EvaluationStage = "uploaded"
    recruiter_decision: Literal["approved", "rejected", "hold"] | None = None
    recruiter_notes: str | None = None
    final_outcome: Literal["hired", "rejected", "withdrew", "on_hold"] | None = None

    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)


# ─────────────────────────────────────────────
# INTERVIEW RECORD
# ─────────────────────────────────────────────

class Interview(BaseModel):
    interview_id: str = Field(default_factory=_id)
    evaluation_id: str
    candidate_id: str
    job_id: str
    questions_generated: list[str] = Field(default_factory=list)
    transcript: str | None = None
    ai_analysis: InterviewAnalysis | None = None
    scheduled_at: str | None = None
    completed_at: str | None = None
    created_at: str = Field(default_factory=_now)


# ─────────────────────────────────────────────
# KPI LOG
# ─────────────────────────────────────────────

class KPILog(BaseModel):
    kpi_id: str = Field(default_factory=_id)
    client_id: str
    job_id: str | None = None
    period_start: str
    period_end: str
    candidates_processed: int = 0
    candidates_screened: int = 0
    candidates_interviewed: int = 0
    candidates_hired: int = 0
    candidates_reused: int = 0
    time_to_shortlist_days: float | None = None
    time_to_hire_days: float | None = None
    hours_saved_estimate: float | None = None
    reuse_rate_pct: float | None = None
    created_at: str = Field(default_factory=_now)


# ─────────────────────────────────────────────
# RANKED CANDIDATE (output of screening)
# ─────────────────────────────────────────────

class RankedCandidate(BaseModel):
    candidate: Candidate
    evaluation: Evaluation
    rank: int
    score: float


# ─────────────────────────────────────────────
# WORKFLOW CONTEXT (passed through pipeline)
# ─────────────────────────────────────────────

class HRWorkflowContext(BaseModel):
    job: Job
    candidates: list[Candidate] = Field(default_factory=list)
    evaluations: list[Evaluation] = Field(default_factory=list)
    interviews: list[Interview] = Field(default_factory=list)
    ranked: list[RankedCandidate] = Field(default_factory=list)
    report_path: str | None = None
