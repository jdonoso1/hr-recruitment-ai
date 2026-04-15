from __future__ import annotations

import json
import os
import re
from pathlib import Path

import anthropic
import pdfplumber

MODEL = "claude-haiku-4-5-20251001"  # lightweight — just extraction


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Extract raw text from a PDF CV."""
    text_parts = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text.strip())
    return "\n\n".join(text_parts)


def extract_text_from_string(text: str) -> str:
    """Pass-through for plain text CVs."""
    return text.strip()


_EXTRACTION_PROMPT = """
You are a CV data extraction specialist. Extract structured information from the CV text below.

Return valid JSON with these exact keys:
{
  "name": string,
  "email": string or null,
  "phone": string or null,
  "linkedin_url": string or null,
  "location": string or null,
  "languages": [string],
  "current_role": string or null,
  "current_company": string or null,
  "years_experience": number or null,
  "industries": [string],
  "skills": [string],
  "salary_expectation": number or null,
  "salary_currency": "USD",
  "relocation_ok": boolean,
  "availability": string or null,
  "recommended_roles": [string],
  "recommended_industries": [string]
}

Rules:
- years_experience: calculate from work history if not stated explicitly
- skills: extract all technical and soft skills mentioned
- recommended_roles: infer 2-3 roles this person is suited for based on their background
- recommended_industries: infer from their experience
- Return null for fields not found — never guess
- Return only JSON, no explanation
""".strip()


def parse_cv(raw_text: str) -> dict:
    """
    Send CV text to Claude Haiku and extract structured candidate data.
    Returns a dict matching the Candidate model fields.
    """
    client = _client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"{_EXTRACTION_PROMPT}\n\n---CV START---\n{raw_text}\n---CV END---",
            }
        ],
    )
    text = response.content[0].text.strip()

    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    return json.loads(text)


def _coerce(parsed: dict) -> dict:
    """Ensure boolean fields are never None."""
    for key in ("relocation_ok", "reusable"):
        if parsed.get(key) is None:
            parsed[key] = False
    for key in ("languages", "industries", "skills", "recommended_roles", "recommended_industries"):
        if parsed.get(key) is None:
            parsed[key] = []
    return parsed


def ingest_cv_file(pdf_path: str | Path, client_id: str) -> dict:
    """
    Full pipeline: PDF → raw text → structured candidate dict.
    Returns a dict ready to construct a Candidate model.
    """
    path = Path(pdf_path)
    raw_text = extract_text_from_pdf(path)
    parsed = _coerce(parse_cv(raw_text))
    parsed["cv_raw_text"] = raw_text
    parsed["cv_file_path"] = str(path.resolve())
    parsed["client_id"] = client_id
    return parsed


def ingest_cv_text(text: str, client_id: str) -> dict:
    """
    Full pipeline: plain text → structured candidate dict.
    """
    parsed = _coerce(parse_cv(text))
    parsed["cv_raw_text"] = text
    parsed["cv_file_path"] = None
    parsed["client_id"] = client_id
    return parsed


def ingest_linkedin_text(pasted_text: str, client_id: str) -> dict:
    """
    Parse manually pasted LinkedIn profile text.
    (No scraping — recruiter copies and pastes the profile.)
    Returns same structure as ingest_cv_text.
    """
    return ingest_cv_text(pasted_text, client_id)
