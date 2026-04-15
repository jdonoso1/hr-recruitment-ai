# HR Recruitment AI

AI-powered recruitment platform for consultants — end-to-end from job setup to candidate presentation.

## What it does

Two integrated modules:

**Recruitment App** (`src/app/`)
- Manage clients, jobs, and candidates via a web dashboard
- Candidate hunting & outreach with AI agents (CompanyMapper, RoleIdentifier)
- Built with FastAPI + SQLModel + Jinja2 templates

**HR Platform** (`src/hr_platform/`)
- CV ingestion and parsing (PDF → structured data)
- AI screening, enrichment, and interview simulation agents
- Candidate presentation generation (PowerPoint)
- Powered by Claude (Anthropic) via multi-agent pipeline

## Stack

- Python 3.11+ / FastAPI / SQLModel
- Claude (Anthropic SDK) for all AI agents
- Jinja2 for web UI
- SQLite for persistence
- pdfplumber + python-pptx for document handling

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env  # add your ANTHROPIC_API_KEY
```

**Run the web app:**
```bash
uvicorn src.app.main:app --reload
```

**Run the CV pipeline:**
```bash
hr screen --cv path/to/cv.pdf --job job.json
```

## Project Structure

```
src/
├── app/               # Recruitment web app (jobs, clients, hunting)
│   ├── agents/        # Hunting & outreach AI agents
│   ├── routes/        # FastAPI routers
│   └── main.py
└── hr_platform/       # CV pipeline & screening
    ├── agents/        # Screening, enrichment, interview, presentation
    ├── ingestion/     # CV parser
    ├── db/            # Database layer
    └── orchestrator.py
migrations/            # SQL schema migrations
templates/             # Jinja2 HTML templates
tests/                 # Pytest test suite
```
