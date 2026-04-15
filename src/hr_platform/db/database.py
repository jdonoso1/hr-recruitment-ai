from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from ..models.schema import Candidate, Client, Evaluation, Interview, Job, KPILog

DB_PATH = os.environ.get("DATABASE_URL", "hr_platform.db").replace("sqlite:///", "")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(migrations_path: str | None = None) -> None:
    """Run migrations to create tables."""
    if migrations_path is None:
        here = Path(__file__).parent.parent.parent.parent
        migrations_path = str(here / "migrations" / "001_initial.sql")
    sql = Path(migrations_path).read_text()
    with get_conn() as conn:
        conn.executescript(sql)


# ─── Clients ──────────────────────────────────────────────────────────────────

def save_client(c: Client) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO clients
            (client_id, name, contact_name, email, phone, plan, active, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (c.client_id, c.name, c.contact_name, c.email, c.phone,
              c.plan, int(c.active), c.created_at, c.updated_at))


def get_client(client_id: str) -> Client | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM clients WHERE client_id=?", (client_id,)).fetchone()
    return Client(**dict(row)) if row else None


# ─── Jobs ─────────────────────────────────────────────────────────────────────

def save_job(j: Job) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO jobs
            (job_id, client_id, title, company, description, required_skills,
             nice_to_have, experience_min, experience_max, location, remote_ok,
             salary_min, salary_max, status, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (j.job_id, j.client_id, j.title, j.company, j.description,
              json.dumps(j.required_skills), json.dumps(j.nice_to_have),
              j.experience_min, j.experience_max, j.location, int(j.remote_ok),
              j.salary_min, j.salary_max, j.status, j.created_at, j.updated_at))


def get_job(job_id: str) -> Job | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["required_skills"] = json.loads(d["required_skills"])
    d["nice_to_have"] = json.loads(d["nice_to_have"])
    d["remote_ok"] = bool(d["remote_ok"])
    return Job(**d)


def list_jobs(client_id: str) -> list[Job]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM jobs WHERE client_id=?", (client_id,)).fetchall()
    jobs = []
    for row in rows:
        d = dict(row)
        d["required_skills"] = json.loads(d["required_skills"])
        d["nice_to_have"] = json.loads(d["nice_to_have"])
        d["remote_ok"] = bool(d["remote_ok"])
        jobs.append(Job(**d))
    return jobs


# ─── Candidates ───────────────────────────────────────────────────────────────

def save_candidate(c: Candidate) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO candidates
            (candidate_id, client_id, name, email, phone, linkedin_url, location,
             languages, current_role, current_company, years_experience, industries,
             skills, cv_raw_text, cv_file_path, salary_expectation, salary_currency,
             relocation_ok, availability, reusable, recommended_roles,
             recommended_industries, priority_level, notes, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (c.candidate_id, c.client_id, c.name, c.email, c.phone,
              c.linkedin_url, c.location, json.dumps(c.languages),
              c.current_role, c.current_company, c.years_experience,
              json.dumps(c.industries), json.dumps(c.skills),
              c.cv_raw_text, c.cv_file_path, c.salary_expectation,
              c.salary_currency, int(c.relocation_ok), c.availability,
              int(c.reusable), json.dumps(c.recommended_roles),
              json.dumps(c.recommended_industries), c.priority_level,
              c.notes, c.created_at, c.updated_at))


def _row_to_candidate(row) -> Candidate:
    d = dict(row)
    for f in ("languages", "industries", "skills", "recommended_roles", "recommended_industries"):
        d[f] = json.loads(d[f])
    d["relocation_ok"] = bool(d["relocation_ok"])
    d["reusable"] = bool(d["reusable"])
    return Candidate(**d)


def get_candidate(candidate_id: str) -> Candidate | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM candidates WHERE candidate_id=?", (candidate_id,)).fetchone()
    return _row_to_candidate(row) if row else None


def search_candidates(client_id: str, skill: str | None = None,
                      min_experience: float | None = None,
                      industry: str | None = None,
                      reusable_only: bool = False) -> list[Candidate]:
    """Basic candidate search — filter by skill, experience, industry."""
    query = "SELECT * FROM candidates WHERE client_id=?"
    params: list = [client_id]

    if reusable_only:
        query += " AND reusable=1"
    if min_experience is not None:
        query += " AND years_experience >= ?"
        params.append(min_experience)
    if skill:
        query += " AND skills LIKE ?"
        params.append(f"%{skill}%")
    if industry:
        query += " AND industries LIKE ?"
        params.append(f"%{industry}%")

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_candidate(r) for r in rows]


# ─── Evaluations ──────────────────────────────────────────────────────────────

def save_evaluation(e: Evaluation) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO evaluations
            (evaluation_id, candidate_id, job_id, client_id,
             screening_score, skills_score, experience_score, culture_score,
             screening_reasoning, strengths, weaknesses, red_flags,
             interview_score, interview_notes, interview_reasoning,
             communication_score, technical_score, motivation_score,
             stage, recruiter_decision, recruiter_notes, final_outcome,
             created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (e.evaluation_id, e.candidate_id, e.job_id, e.client_id,
              e.screening_score, e.skills_score, e.experience_score, e.culture_score,
              e.screening_reasoning, json.dumps(e.strengths),
              json.dumps(e.weaknesses), json.dumps(e.red_flags),
              e.interview_score, e.interview_notes, e.interview_reasoning,
              e.communication_score, e.technical_score, e.motivation_score,
              e.stage, e.recruiter_decision, e.recruiter_notes, e.final_outcome,
              e.created_at, e.updated_at))


def get_evaluations_for_job(job_id: str) -> list[Evaluation]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM evaluations WHERE job_id=?", (job_id,)).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        for f in ("strengths", "weaknesses", "red_flags"):
            d[f] = json.loads(d[f])
        result.append(Evaluation(**d))
    return result


# ─── Interviews ───────────────────────────────────────────────────────────────

def save_interview(i: Interview) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO interviews
            (interview_id, evaluation_id, candidate_id, job_id,
             questions_generated, transcript, ai_analysis,
             scheduled_at, completed_at, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (i.interview_id, i.evaluation_id, i.candidate_id, i.job_id,
              json.dumps(i.questions_generated), i.transcript,
              i.ai_analysis.model_dump_json() if i.ai_analysis else None,
              i.scheduled_at, i.completed_at, i.created_at))


# ─── KPI ──────────────────────────────────────────────────────────────────────

def save_kpi(k: KPILog) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO kpi_logs
            (kpi_id, client_id, job_id, period_start, period_end,
             candidates_processed, candidates_screened, candidates_interviewed,
             candidates_hired, candidates_reused, time_to_shortlist_days,
             time_to_hire_days, hours_saved_estimate, reuse_rate_pct, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (k.kpi_id, k.client_id, k.job_id, k.period_start, k.period_end,
              k.candidates_processed, k.candidates_screened, k.candidates_interviewed,
              k.candidates_hired, k.candidates_reused, k.time_to_shortlist_days,
              k.time_to_hire_days, k.hours_saved_estimate, k.reuse_rate_pct, k.created_at))
