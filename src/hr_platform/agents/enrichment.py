from __future__ import annotations

import json
import os

import anthropic

from ..models.schema import Candidate, Evaluation, Interview

MODEL = "claude-haiku-4-5-20251001"  # lightweight enrichment task

_ENRICHMENT_PROMPT = """
You are a candidate intelligence specialist. Based on all data collected about
this candidate (CV, screening evaluation, and interview if available), enrich
their profile with strategic intelligence for future use.

Return JSON with keys:
- recommended_roles: list of 3–5 job titles this person is suited for
- recommended_industries: list of 2–4 industries they'd thrive in
- priority_level: "low" | "normal" | "high" (based on overall quality)
- reusable: true if this candidate should be kept in the talent pool
- notes: 2–3 sentences of strategic notes for future recruiters

Return only JSON.
""".strip()


def enrich_candidate(
    candidate: Candidate,
    evaluation: Evaluation,
    interview: Interview | None = None,
) -> Candidate:
    """
    Enrich a candidate's intelligence fields after screening and (optionally) interview.
    Updates and returns the candidate in place.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    interview_summary = "No interview conducted."
    if interview and interview.ai_analysis:
        a = interview.ai_analysis
        interview_summary = (
            f"Interview score: {a.overall_score}/10. "
            f"Recommendation: {a.hire_recommendation}. "
            f"Strengths: {a.strengths}. Concerns: {a.concerns}."
        )

    user_prompt = f"""
CANDIDATE: {candidate.name}
Current role: {candidate.current_role} at {candidate.current_company}
Experience: {candidate.years_experience} years
Skills: {candidate.skills}
Industries: {candidate.industries}

SCREENING RESULT:
Overall score: {evaluation.screening_score}/10
Strengths: {evaluation.strengths}
Weaknesses: {evaluation.weaknesses}
Red flags: {evaluation.red_flags}

INTERVIEW:
{interview_summary}
""".strip()

    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=_ENRICHMENT_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    data = json.loads(text)

    candidate.recommended_roles = data.get("recommended_roles", candidate.recommended_roles)
    candidate.recommended_industries = data.get("recommended_industries", candidate.recommended_industries)
    candidate.priority_level = data.get("priority_level", candidate.priority_level)
    candidate.reusable = data.get("reusable", candidate.reusable)
    candidate.notes = data.get("notes", candidate.notes)

    return candidate
