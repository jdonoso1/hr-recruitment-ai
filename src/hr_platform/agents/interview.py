from __future__ import annotations

import json
import os

import anthropic

from ..models.schema import Candidate, Evaluation, Interview, InterviewAnalysis, Job

MODEL = "claude-haiku-4-5-20251001"

_QUESTION_PROMPT = """
You are a senior HR interviewer designing a structured interview.
Generate tailored interview questions for this candidate and role.

Return JSON with key: questions (list of strings, 8–12 questions)

Mix:
- 2–3 technical/skills questions specific to the role
- 2–3 behavioral questions (STAR format prompts)
- 2 motivation/culture fit questions
- 1–2 questions addressing any red flags or gaps in the CV
- 1 closing question

Be specific to this candidate — reference their background.
Return only JSON.
""".strip()

_ANALYSIS_PROMPT = """
You are an expert interview evaluator. Analyze the interview transcript or notes
and produce a structured evaluation of the candidate.

Scoring (1–10):
- overall: overall interview performance
- communication: clarity, structure, confidence of responses
- technical: depth and accuracy of technical answers
- motivation: genuine interest in the role and company

hire_recommendation options: strong_yes | yes | neutral | no | strong_no

Return JSON with keys:
overall_score, communication_score, technical_score, motivation_score,
reasoning, strengths (list), concerns (list),
recommended_questions (list — follow-up questions if a second interview is needed),
hire_recommendation

Return only JSON.
""".strip()


def generate_questions(job: Job, candidate: Candidate, evaluation: Evaluation) -> list[str]:
    """Generate tailored interview questions for a candidate."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    user_prompt = f"""
ROLE: {job.title} at {job.company}
CANDIDATE: {candidate.name} — {candidate.current_role} at {candidate.current_company}
SKILLS: {candidate.skills}
EXPERIENCE: {candidate.years_experience} years
STRENGTHS IDENTIFIED: {evaluation.strengths}
WEAKNESSES IDENTIFIED: {evaluation.weaknesses}
RED FLAGS: {evaluation.red_flags}
JOB REQUIREMENTS: {job.required_skills}
""".strip()

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=_QUESTION_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    data = json.loads(text)
    return data.get("questions", [])


def analyze_interview(
    job: Job,
    candidate: Candidate,
    transcript: str,
    questions: list[str],
) -> InterviewAnalysis:
    """Analyze an interview transcript and return structured evaluation."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    user_prompt = f"""
ROLE: {job.title} at {job.company}
CANDIDATE: {candidate.name}
REQUIRED SKILLS: {job.required_skills}
INTERVIEW QUESTIONS USED: {questions}

TRANSCRIPT / NOTES:
{transcript}
""".strip()

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=_ANALYSIS_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    data = json.loads(text)
    return InterviewAnalysis(**data)


def run_interview_stage(
    job: Job,
    candidate: Candidate,
    evaluation: Evaluation,
    transcript: str | None = None,
) -> Interview:
    """
    Full interview stage:
    1. Generate questions
    2. If transcript provided, analyze it
    Returns populated Interview record.
    """
    questions = generate_questions(job, candidate, evaluation)

    analysis = None
    if transcript:
        analysis = analyze_interview(job, candidate, transcript, questions)

        # Update evaluation with interview scores
        evaluation.interview_score = analysis.overall_score
        evaluation.interview_reasoning = analysis.reasoning
        evaluation.communication_score = analysis.communication_score
        evaluation.technical_score = analysis.technical_score
        evaluation.motivation_score = analysis.motivation_score
        evaluation.stage = "evaluated"

    return Interview(
        evaluation_id=evaluation.evaluation_id,
        candidate_id=candidate.candidate_id,
        job_id=job.job_id,
        questions_generated=questions,
        transcript=transcript,
        ai_analysis=analysis,
    )
