from __future__ import annotations

import json
import os

import anthropic

from ..models.schema import Candidate, Evaluation, Job, RankedCandidate, ScoreBreakdown

MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT = """
You are an expert talent acquisition specialist and CV screening analyst.
Your job is to evaluate candidates against a specific job description and produce
a rigorous, objective, and structured scoring assessment.

Scoring criteria:
- skills_match (1–10): how well the candidate's skills match required + nice-to-have
- experience_match (1–10): years, seniority level, and relevance of past roles
- culture_fit (1–10): communication style, career trajectory alignment, stability
- overall (1–10): weighted average — skills 40%, experience 40%, culture 20%

Be critical. A 10 means nearly perfect. A 5 means average fit.
Flag red flags honestly — gaps, short tenures, mismatched seniority, etc.

Return only valid JSON. No explanations outside the JSON.
""".strip()


def _build_prompt(job: Job, candidate: Candidate) -> str:
    return f"""
JOB REQUIREMENTS:
Title: {job.title}
Company: {job.company}
Description: {job.description}
Required skills: {job.required_skills}
Nice to have: {job.nice_to_have}
Experience required: {job.experience_min}–{job.experience_max} years
Location: {job.location} | Remote: {job.remote_ok}
Salary range: {job.salary_min}–{job.salary_max} {' USD' if job.salary_min else ''}

CANDIDATE PROFILE:
Name: {candidate.name}
Current role: {candidate.current_role} at {candidate.current_company}
Years of experience: {candidate.years_experience}
Skills: {candidate.skills}
Industries: {candidate.industries}
Location: {candidate.location} | Relocation: {candidate.relocation_ok}
Salary expectation: {candidate.salary_expectation} {candidate.salary_currency}
Availability: {candidate.availability}
Languages: {candidate.languages}

CV TEXT:
{candidate.cv_raw_text or 'Not available'}

Return JSON with keys: overall, skills_match, experience_match, culture_fit,
reasoning, strengths (list), weaknesses (list), red_flags (list)
""".strip()


def screen_candidate(job: Job, candidate: Candidate) -> tuple[Evaluation, ScoreBreakdown]:
    """
    Screen a single candidate against a job.
    Returns updated Evaluation + ScoreBreakdown.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_prompt(job, candidate)}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    data = json.loads(text)
    score = ScoreBreakdown(**data)

    evaluation = Evaluation(
        candidate_id=candidate.candidate_id,
        job_id=job.job_id,
        client_id=job.client_id,
        screening_score=score.overall,
        skills_score=score.skills_match,
        experience_score=score.experience_match,
        culture_score=score.culture_fit,
        screening_reasoning=score.reasoning,
        strengths=score.strengths,
        weaknesses=score.weaknesses,
        red_flags=score.red_flags,
        stage="screened",
    )

    return evaluation, score


def screen_all(job: Job, candidates: list[Candidate]) -> list[RankedCandidate]:
    """
    Screen all candidates for a job and return ranked list (highest score first).
    """
    results: list[RankedCandidate] = []

    for candidate in candidates:
        evaluation, score = screen_candidate(job, candidate)
        results.append(
            RankedCandidate(
                candidate=candidate,
                evaluation=evaluation,
                rank=0,  # assigned below
                score=score.overall,
            )
        )

    # Sort by score descending, assign ranks
    results.sort(key=lambda r: r.score, reverse=True)
    for i, r in enumerate(results, start=1):
        r.rank = i

    return results
