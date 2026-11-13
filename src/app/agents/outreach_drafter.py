"""OutreachDrafterAgent — Drafts personalized first-touch outreach per candidate

For each approved candidate, generates:
- a short LinkedIn message (<= 1000 chars)
- a more detailed email (<= 2000 chars)

Drafts are grounded in the job (title, seniority, description) and the candidate's
current role/company. They are never sent automatically: they land as
OutreachDraft records with status=pending_review for the consultant to review.

If the Claude API is unavailable, `build_template_draft()` produces a plain,
clearly-labelled template draft from the same context so the consultant still
has something to edit.
"""

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import AgentResponse, BaseAgent

logger = logging.getLogger(__name__)

LINKEDIN_MAX_CHARS = 1000
EMAIL_MAX_CHARS = 2000
TRIM_NOTE = "[Trimmed — too long]"
TEMPLATE_NOTE = "[Template draft — AI drafting unavailable. Personalize before approving.]"


# ===== Request / Response models =====

class JobSummary(BaseModel):
    """Job context used to ground the outreach"""
    id: int
    title: str
    description: str
    seniority: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    required_experience_years: Optional[int] = None


class CandidateSummary(BaseModel):
    """Candidate being contacted"""
    name: str
    current_title: str
    current_company: str
    linkedin_url: Optional[str] = None


class TargetCompanySummary(BaseModel):
    """Company where the candidate currently works"""
    name: str
    industry: str
    size_description: str


class OutreachDrafterRequest(BaseModel):
    """Everything the agent needs to draft outreach for one candidate"""
    job: JobSummary
    candidate: CandidateSummary
    company: TargetCompanySummary


class OutreachDrafterResponse(BaseModel):
    """Drafted messages for one candidate"""
    linkedin_message: str = Field(..., min_length=1)
    email_message: str = Field(..., min_length=1)


# ===== Helpers =====

def trim_message(message: str, max_chars: int) -> str:
    """Trim a message to max_chars, appending a visible note when trimmed."""
    message = message.strip()
    if len(message) <= max_chars:
        return message
    logger.warning("Outreach message too long (%d > %d chars); trimming", len(message), max_chars)
    keep = max_chars - len(TRIM_NOTE) - 1
    return message[:keep].rstrip() + "\n" + TRIM_NOTE


def _first_name(full_name: str) -> str:
    return full_name.split()[0] if full_name.strip() else "there"


def _role_label(job: "JobSummary") -> str:
    """'Senior Python Engineer' + 'Senior' -> 'Senior Python Engineer' (no doubled seniority)."""
    if job.seniority.lower() in job.title.lower():
        return job.title
    return f"{job.seniority} {job.title}"


def build_template_draft(request: OutreachDrafterRequest) -> OutreachDrafterResponse:
    """Deterministic fallback draft built only from the request's real data."""
    job, cand = request.job, request.candidate
    first = _first_name(cand.name)
    role = _role_label(job)

    linkedin = (
        f"Hi {first}, I came across your work as {cand.current_title} at "
        f"{cand.current_company} and thought of you for a {role} role I'm "
        f"recruiting for. Would you be open to a short "
        f"conversation to hear more?\n\n{TEMPLATE_NOTE}"
    )

    salary = ""
    if job.salary_min and job.salary_max:
        salary = f" The compensation range is ${job.salary_min:,}–${job.salary_max:,}."
    experience = ""
    if job.required_experience_years:
        experience = f" We're looking for around {job.required_experience_years}+ years of relevant experience."

    email = (
        f"Subject: {role} opportunity\n\n"
        f"Hi {first},\n\n"
        f"I'm reaching out because your experience as {cand.current_title} at "
        f"{cand.current_company} stood out to me. I'm currently recruiting for a "
        f"{role} position.{experience}{salary}\n\n"
        f"Would you be open to exploring it? Happy to share more details at a time "
        f"that suits you.\n\nBest regards\n\n{TEMPLATE_NOTE}"
    )

    return OutreachDrafterResponse(
        linkedin_message=trim_message(linkedin, LINKEDIN_MAX_CHARS),
        email_message=trim_message(email, EMAIL_MAX_CHARS),
    )


# ===== Agent =====

class OutreachDrafterAgent(BaseAgent):
    """Generates a LinkedIn message and an email for one candidate."""

    def system_prompt(self) -> str:
        return f"""You are an experienced executive recruiter writing FIRST-TOUCH outreach to a passive candidate.

Write two messages for the candidate described by the user:

1. linkedin_message — a LinkedIn connection/InMail message.
   - Professional, warm, brief (aim for 300-600 characters, hard limit {LINKEDIN_MAX_CHARS}).
2. email_message — a formal email.
   - Start with a "Subject: ..." line, then a blank line, then the body.
   - More detailed: role, seniority, why they fit (hard limit {EMAIL_MAX_CHARS} characters).

Both messages must:
- Address the candidate by first name.
- Reference their current role and company, to show genuine research.
- Mention the specific role and seniority, and why it may be a fit.
- End with a soft call to action ("open to exploring?", "interested in a quick chat?") — never pushy.
- Be suitable as an initial message, not a follow-up.
- Never invent facts about the candidate or the client beyond what is provided.
- Use placeholders like [Your Name] for the sender's signature.

Return the messages by calling the generate_outreach_messages tool."""

    def tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "generate_outreach_messages",
                "description": "Return the drafted LinkedIn message and email for the candidate",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "linkedin_message": {
                            "type": "string",
                            "description": f"LinkedIn message, max {LINKEDIN_MAX_CHARS} characters",
                        },
                        "email_message": {
                            "type": "string",
                            "description": f"Email with Subject line, max {EMAIL_MAX_CHARS} characters",
                        },
                    },
                    "required": ["linkedin_message", "email_message"],
                },
            }
        ]

    def parse_response(self, tool_results: List[Dict[str, Any]]) -> OutreachDrafterResponse:
        """Validate the tool call and enforce length limits.

        Raises ValueError / pydantic.ValidationError if the tool call is missing
        or malformed; run() turns that into an error AgentResponse.
        """
        if not tool_results:
            raise ValueError("Model did not call generate_outreach_messages")

        tool_input = tool_results[0].get("input", {}) or {}
        parsed = OutreachDrafterResponse(**tool_input)
        return OutreachDrafterResponse(
            linkedin_message=trim_message(parsed.linkedin_message, LINKEDIN_MAX_CHARS),
            email_message=trim_message(parsed.email_message, EMAIL_MAX_CHARS),
        )

    def _build_user_message(self, request: OutreachDrafterRequest) -> str:
        job, cand, company = request.job, request.candidate, request.company
        lines = [
            "Draft outreach for this candidate.",
            "",
            "CANDIDATE",
            f"- Name: {cand.name}",
            f"- Current title: {cand.current_title}",
            f"- Current company: {cand.current_company}",
            "",
            "CANDIDATE'S COMPANY",
            f"- Name: {company.name}",
            f"- Industry: {company.industry}",
            f"- Size: {company.size_description}",
            "",
            "ROLE",
            f"- Title: {job.title}",
            f"- Seniority: {job.seniority}",
        ]
        if job.required_experience_years:
            lines.append(f"- Required experience: {job.required_experience_years}+ years")
        if job.salary_min and job.salary_max:
            lines.append(f"- Salary range: ${job.salary_min:,}–${job.salary_max:,}")
        lines += ["- Description:", job.description]
        return "\n".join(lines)

    async def run(self, request: OutreachDrafterRequest) -> AgentResponse:
        """Draft messages for one candidate. Never raises; errors are in AgentResponse."""
        return await super().run(request)
