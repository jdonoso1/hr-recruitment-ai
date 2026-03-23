---
phase: 01-foundation-job-project-setup
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - pyproject.toml
  - src/app/main.py
  - src/app/db.py
  - src/app/models.py
  - src/app/__init__.py
  - .env.example
  - .gitignore
  - tests/__init__.py
  - tests/conftest.py
  - tests/test_models.py
  - tests/test_routes.py
autonomous: true
requirements: [JOB-01, JOB-02, JOB-03, JOB-04]
user_setup: []

must_haves:
  truths:
    - "Python project is initialized with uv tooling and FastAPI dependency"
    - "SQLModel data models exist for Client and Job with all JOB-01 and JOB-02 fields"
    - "Job model has JSON columns for target_industries and target_company_types"
    - "Job model includes JobStatus enum for JOB-03 pipeline tracking"
    - "Database connection is established and tables can be created"
    - "Project structure follows FastAPI conventions (main.py, models.py, db.py)"
    - "Test infrastructure exists with pytest fixtures, test stubs, and conftest configuration"
  artifacts:
    - path: "pyproject.toml"
      provides: "Project metadata, Python version, all dependencies (FastAPI, SQLModel, uvicorn, pytest, pytest-asyncio)"
      must_contain: ["fastapi", "sqlmodel", "uvicorn", "pytest", "pytest-asyncio"]
    - path: "src/app/models.py"
      provides: "SQLModel Client and Job models with all fields, JobStatus enum"
      exports: ["Client", "Job", "JobStatus"]
      min_lines: 50
    - path: "src/app/db.py"
      provides: "Database engine, session management, initialization function"
      exports: ["engine", "get_session", "create_db_tables"]
      min_lines: 30
    - path: "src/app/main.py"
      provides: "FastAPI app instance with lifespan event to create tables on startup"
      min_lines: 20
    - path: "tests/conftest.py"
      provides: "Pytest configuration, SQLite test fixture, database session fixture"
      must_contain: ["@pytest.fixture", "sqlite:///:memory:", "yield"]
    - path: "tests/test_models.py"
      provides: "Test module stubs for Client and Job model tests"
      min_lines: 5
    - path: "tests/test_routes.py"
      provides: "Test module stubs for route tests (filled in Plan 02)"
      min_lines: 5
  key_links:
    - from: "src/app/main.py"
      to: "src/app/db.py"
      via: "import get_session, engine"
      pattern: "from.*db import"
    - from: "src/app/main.py"
      to: "src/app/models.py"
      via: "import SQLModel classes"
      pattern: "from.*models import.*Client.*Job"
    - from: "src/app/db.py"
      to: "src/app/models.py"
      via: "create_all uses model metadata"
      pattern: "SQLModel.metadata.create_all"
    - from: "tests/conftest.py"
      to: "src/app/models.py"
      via: "import models for table creation"
      pattern: "from src.app.models import"
---

<objective>
Set up Phase 1 project foundation: initialize FastAPI project with uv, create SQLModel data models (Client + Job) with all JOB-01, JOB-02, JOB-03, JOB-04 fields, establish database connection with SQLite, create test infrastructure with pytest fixtures, and prepare for API route implementation.

Purpose: Build the data layer, test infrastructure, and project structure that all subsequent Phase 1 tasks depend on. Locked decisions (SQLModel, SQLite, uv) are implemented here. Wave 0 test fixtures ensure all verification commands can run.

Output: Working Python project with models, database initialization, test fixtures, and app structure ready for API routes in Plan 02.
</objective>

<execution_context>
@/Users/juanjavierdonoso/.claude/get-shit-done/workflows/execute-plan.md
@/Users/juanjavierdonoso/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-foundation-job-project-setup/01-CONTEXT.md
@.planning/phases/01-foundation-job-project-setup/01-RESEARCH.md

Locked Decisions:
- ORM: SQLModel (Pydantic v2 + SQLAlchemy unified models)
- Database: SQLite for v1 (postgres-compatible design)
- Tooling: uv for package management
- Framework: FastAPI
- Project structure: src/app/ layout with separate models.py, db.py, main.py
- Testing: pytest + pytest-asyncio, conftest with in-memory SQLite fixture

Reference Model Definitions:
From 01-CONTEXT.md — these are the exact fields required:

Client model:
- id: int | None (primary key)
- name: str
- created_at: datetime (default utcnow)

Job model:
- id: int | None (primary key)
- client_id: int (foreign key to client.id)
- title: str
- description: str
- seniority: str (enum: Senior, Manager, Director, etc.)
- salary_min: int | None
- salary_max: int | None
- required_experience_years: int | None
- target_industries: list[str] (JSON column) — JOB-02
- target_company_types: list[str] (JSON column) — JOB-02
- status: JobStatus (enum: hunting, shortlisting, interviewing, closed) — JOB-03
- created_at: datetime (default utcnow)
- updated_at: datetime (default utcnow)

JobStatus enum values: hunting, shortlisting, interviewing, closed
</context>

<tasks>

<task type="auto">
  <name>Task 0 (Wave 0): Create test infrastructure with pytest fixtures and conftest</name>
  <files>
    tests/__init__.py
    tests/conftest.py
    tests/test_models.py
    tests/test_routes.py
    pyproject.toml
  </files>
  <read_first>
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/pyproject.toml (to add pytest configuration)
  </read_first>
  <action>
1. Create tests/ directory structure:
   - Create tests/__init__.py (empty)
   - Create tests/conftest.py with pytest fixtures for database testing
   - Create tests/test_models.py with stubs
   - Create tests/test_routes.py with stubs

2. Write tests/conftest.py with in-memory SQLite fixture for testing:
```python
import pytest
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool

@pytest.fixture(name="db_session")
def db_session_fixture():
    """Create in-memory SQLite database session for testing.

    Each test gets a fresh database (StaticPool for single conn).
    """
    # Import models to register them with SQLModel.metadata
    from src.app.models import Client, Job, JobStatus

    # Create in-memory SQLite engine
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    SQLModel.metadata.create_all(engine)

    # Yield session for test
    with Session(engine) as session:
        yield session

@pytest.fixture
def client_data():
    """Sample client data for tests"""
    return {
        "name": "Test Client LLC"
    }

@pytest.fixture
def job_data(client_data):
    """Sample job data for tests"""
    return {
        "client_id": 1,
        "title": "Senior Python Engineer",
        "description": "Build scalable systems with Python and FastAPI",
        "seniority": "Senior",
        "salary_min": 150000,
        "salary_max": 200000,
        "required_experience_years": 5,
        "target_industries": ["Technology", "Finance"],
        "target_company_types": ["Startup", "Tech Company"],
    }
```

3. Create tests/test_models.py (stubs):
```python
"""Tests for SQLModel data models (Client, Job)"""

def test_client_model_stub():
    """Placeholder for client model tests - implemented in later task"""
    pass

def test_job_model_stub():
    """Placeholder for job model tests - implemented in later task"""
    pass
```

4. Create tests/test_routes.py (stubs):
```python
"""Tests for FastAPI routes (jobs, clients)"""

def test_job_routes_stub():
    """Placeholder for job route tests - implemented in Plan 02"""
    pass

def test_client_routes_stub():
    """Placeholder for client route tests - implemented in Plan 02"""
    pass
```

5. Update pyproject.toml to add pytest configuration:
   - Add under [tool.pytest.ini_options]:
     ```toml
     [tool.pytest.ini_options]
     testpaths = ["tests"]
     python_files = ["test_*.py"]
     python_classes = ["Test*"]
     python_functions = ["test_*"]
     asyncio_mode = "auto"
     ```
   - Verify pytest-asyncio is in dev dependencies

6. Create tests/__init__.py (empty file for Python package recognition)
  </action>
  <verify>
    <automated>
      test -f /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/tests/__init__.py && \
      test -f /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/tests/conftest.py && \
      grep -q "@pytest.fixture" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/tests/conftest.py && \
      grep -q "sqlite:///:memory:" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/tests/conftest.py && \
      test -f /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/tests/test_models.py && \
      test -f /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/tests/test_routes.py && \
      grep -q "asyncio_mode = \"auto\"" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/pyproject.toml && \
      cd /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai && uv run pytest tests/ --collect-only 2>&1 | grep -q "test_" && \
      echo "PASS" || echo "FAIL"
    </automated>
  </verify>
  <done>
    - tests/ directory created with __init__.py, conftest.py, test_models.py, test_routes.py
    - conftest.py has pytest fixture for in-memory SQLite database
    - conftest.py has fixtures for sample client_data and job_data
    - test_models.py and test_routes.py have stub test functions
    - pyproject.toml includes [tool.pytest.ini_options] with asyncio_mode = "auto"
    - pytest can collect tests: `uv run pytest tests/ --collect-only` runs without error
  </done>
</task>

<task type="auto">
  <name>Task 1: Initialize FastAPI project with uv and create project structure</name>
  <files>
    pyproject.toml
    .env.example
    .gitignore
    src/app/__init__.py
    src/app/main.py
  </files>
  <read_first>
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/.gitignore (if exists, to see existing patterns)
  </read_first>
  <action>
1. Initialize uv project structure:
   - Run: `uv init --name hr-recruitment-ai --python 3.14` in project root
   - This creates pyproject.toml with basic metadata

2. Update pyproject.toml with all required dependencies:
   - Add to [project] dependencies: ["fastapi>=0.111.0", "sqlmodel>=0.0.37", "uvicorn[standard]>=0.27.0", "pydantic>=2.12.5", "python-dotenv>=1.0.0"]
   - Add to [project] optional-dependencies:
     - dev = ["pytest>=9.0.0", "pytest-asyncio>=0.24.0", "httpx>=0.26.0"]
   - Set requires-python = ">=3.14"

3. Create project structure:
   - Create src/ directory if not exists
   - Create src/app/ directory
   - Create src/app/__init__.py (empty or with __version__)

4. Create .env.example with placeholder values:
   ```
   DATABASE_URL=sqlite:///./hr_recruitment.db
   ENVIRONMENT=development
   ```

5. Create/update .gitignore to include:
   - *.db (SQLite database files)
   - *.db-journal
   - .env (not .env.example)
   - __pycache__/
   - .pytest_cache/
   - .venv/
   - dist/
   - build/
   - *.egg-info/

6. Create src/app/main.py skeleton (minimal FastAPI app):
   ```python
   from contextlib import asynccontextmanager
   from fastapi import FastAPI
   from fastapi.staticfiles import StaticFiles
   from fastapi.templating import Jinja2Templates
   from pathlib import Path

   from .db import create_db_tables

   # Lifespan event to create tables on startup
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       # Startup: create database tables
       create_db_tables()
       yield
       # Shutdown: nothing for now

   app = FastAPI(title="HR Recruitment AI", lifespan=lifespan)

   # Health check endpoint
   @app.get("/health")
   async def health():
       return {"status": "ok"}
   ```

7. Run: `uv sync` to install dependencies into virtual environment
  </action>
  <verify>
    <automated>
      # Check pyproject.toml has all deps
      grep -q "fastapi" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/pyproject.toml && \
      grep -q "sqlmodel" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/pyproject.toml && \
      grep -q "uvicorn" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/pyproject.toml && \
      # Check main.py exists and has lifespan
      grep -q "asynccontextmanager" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/main.py && \
      # Check .env.example exists
      test -f /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/.env.example && \
      echo "PASS" || echo "FAIL"
    </automated>
  </verify>
  <done>
    - pyproject.toml exists with FastAPI, SQLModel, uvicorn, pytest dependencies
    - src/app/main.py created with FastAPI app and lifespan event
    - .env.example exists with DATABASE_URL placeholder
    - .gitignore includes *.db, .env, __pycache__
    - Project can be run with `uv run uvicorn app.main:app --reload` (after db.py is created)
  </done>
</task>

<task type="auto">
  <name>Task 2: Create SQLModel data models for Client and Job with JobStatus enum</name>
  <files>
    src/app/models.py
  </files>
  <read_first>
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/.planning/phases/01-foundation-job-project-setup/01-CONTEXT.md (lines 88-114 for model definitions)
  </read_first>
  <action>
Create src/app/models.py with SQLModel Client and Job models exactly as specified in 01-CONTEXT.md:

```python
from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field

class JobStatus(str, Enum):
    """Job pipeline status enum — required for JOB-03"""
    hunting = "hunting"
    shortlisting = "shortlisting"
    interviewing = "interviewing"
    closed = "closed"

class Client(SQLModel, table=True):
    """Client entity for JOB-01 scope (minimal creation)"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Job(SQLModel, table=True):
    """Job posting model — covers JOB-01 (create with fields) and JOB-02 (target industries/types)"""
    id: Optional[int] = Field(default=None, primary_key=True)

    # JOB-01 required fields
    client_id: int = Field(foreign_key="client.id", index=True)
    title: str = Field(index=True)
    description: str
    seniority: str  # e.g., "Senior", "Manager", "Director"

    # JOB-01 optional fields
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    required_experience_years: Optional[int] = None

    # JOB-02 search scope — JSON list columns
    target_industries: List[str] = Field(default=[], sa_column=Column(JSON))
    target_company_types: List[str] = Field(default=[], sa_column=Column(JSON))

    # JOB-03 status tracking
    status: JobStatus = Field(default=JobStatus.hunting, index=True)

    # Lifecycle timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

Notes on implementation:
- Client.name is indexed (for quick lookups in UI dropdowns)
- Job.title, Job.client_id, Job.status all indexed (for filtering/sorting in dashboard)
- JSON columns use Column(JSON) so SQLAlchemy/SQLite handle serialization automatically
- All datetime fields use Field(default_factory=datetime.utcnow) for automatic timestamps
- No methods needed in models yet (just schema for Phase 1)
- Foreign key constraint ensures referential integrity
  </action>
  <verify>
    <automated>
      # Check models.py has JobStatus enum with all 4 values
      grep -q "class JobStatus" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/models.py && \
      grep -q "hunting = " /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/models.py && \
      grep -q "shortlisting = " /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/models.py && \
      # Check Client model
      grep -q "class Client" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/models.py && \
      grep -q "name: str" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/models.py && \
      # Check Job model has all JOB-01 fields
      grep -q "title: str" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/models.py && \
      grep -q "description: str" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/models.py && \
      grep -q "seniority: str" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/models.py && \
      # Check JSON columns for JOB-02
      grep -q "target_industries: List\[str\]" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/models.py && \
      grep -q "target_company_types: List\[str\]" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/models.py && \
      grep -q "sa_column=Column(JSON)" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/models.py && \
      echo "PASS" || echo "FAIL"
    </automated>
  </verify>
  <done>
    - src/app/models.py created with JobStatus enum (4 values)
    - Client model with id, name, created_at fields
    - Job model with all JOB-01 fields: title, description, seniority, salary_min, salary_max, required_experience_years, client_id
    - Job model with JOB-02 JSON columns: target_industries, target_company_types
    - Job model with JOB-03 status field (JobStatus enum)
    - All foreign keys and indexes properly declared
    - All datetime fields with utcnow defaults
  </done>
</task>

<task type="auto">
  <name>Task 3: Create database layer with SQLAlchemy engine and session management</name>
  <files>
    src/app/db.py
  </files>
  <read_first>
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/models.py (to import SQLModel)
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/.env.example (to reference DATABASE_URL pattern)
  </read_first>
  <action>
Create src/app/db.py with SQLAlchemy engine and FastAPI session dependency:

```python
import os
from sqlalchemy.orm import Session
from sqlmodel import SQLModel, create_engine, Session as SQLSession
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Get database URL from environment, default to SQLite file
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hr_recruitment.db")

# Create SQLAlchemy engine
# For SQLite: add check_same_thread=False to allow multiple threads in dev
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL logging during development
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

def create_db_tables():
    """Create all database tables defined in SQLModel models.

    Called on application startup via lifespan event in main.py.
    SQLModel.metadata.create_all uses the engine to execute CREATE TABLE if not exists.
    """
    SQLModel.metadata.create_all(engine)

def get_session():
    """FastAPI dependency for database sessions.

    Usage in route:
    @app.get("/jobs")
    async def list_jobs(session: Session = Depends(get_session)):
        ...
    """
    with SQLSession(engine) as session:
        yield session
```

Notes on implementation:
- DATABASE_URL read from .env via dotenv (allows local dev + prod config without code changes)
- check_same_thread=False only for SQLite (FastAPI async handlers run in threads)
- create_db_tables() is idempotent — safe to call multiple times (creates only if not exists)
- get_session() is a generator dependency for FastAPI's Depends()
- engine created once at module level (singleton pattern)
  </action>
  <verify>
    <automated>
      # Check db.py imports are correct
      grep -q "from sqlmodel import" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/db.py && \
      # Check engine creation
      grep -q "create_engine" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/db.py && \
      grep -q "DATABASE_URL" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/db.py && \
      # Check functions exist
      grep -q "def create_db_tables" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/db.py && \
      grep -q "def get_session" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/db.py && \
      grep -q "SQLModel.metadata.create_all" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/db.py && \
      echo "PASS" || echo "FAIL"
    </automated>
  </verify>
  <done>
    - src/app/db.py created with SQLAlchemy engine
    - create_db_tables() function that runs SQLModel.metadata.create_all()
    - get_session() FastAPI dependency for injecting database sessions
    - DATABASE_URL read from .env file with SQLite default
    - Connection pool properly configured (check_same_thread=False for SQLite)
  </done>
</task>

<task type="auto">
  <name>Task 4: Wire FastAPI app to models and database, verify startup initialization</name>
  <files>
    src/app/main.py
  </files>
  <read_first>
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/main.py (current skeleton)
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/db.py (import create_db_tables)
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/models.py (verify imports work)
  </read_first>
  <action>
Update src/app/main.py to import models and db, ensure lifespan event calls create_db_tables:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pathlib import Path

# Import database and models to ensure SQLModel metadata is loaded
from .db import create_db_tables
from .models import Client, Job, JobStatus  # Import to ensure models are registered

# Lifespan event to create database tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create database tables
    create_db_tables()
    print("Database tables initialized on startup")
    yield
    # Shutdown: cleanup if needed
    print("Application shutting down")

# Create FastAPI app with lifespan event
app = FastAPI(
    title="HR Recruitment AI",
    description="AI-powered recruitment platform for consultants",
    version="0.1.0",
    lifespan=lifespan,
)

# Health check endpoint
@app.get("/health")
async def health():
    """Simple health check endpoint"""
    return {"status": "ok", "message": "HR Recruitment AI API is running"}

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "app": "HR Recruitment AI",
        "version": "0.1.0",
        "docs": "/docs",
    }
```

Key implementation details:
- Import models (Client, Job, JobStatus) so SQLModel metadata is registered before create_all() runs
- Lifespan context manager handles startup/shutdown
- create_db_tables() called in startup, creates all tables defined in models
- Health check endpoint for monitoring
- Root endpoint for basic API info
- All imports use relative paths (from .db, from .models)
  </action>
  <verify>
    <automated>
      # Check main.py imports db and models
      grep -q "from .db import" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/main.py && \
      grep -q "from .models import" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/main.py && \
      # Check lifespan is defined
      grep -q "@asynccontextmanager" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/main.py && \
      grep -q "create_db_tables()" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/main.py && \
      # Check FastAPI app creation
      grep -q "app = FastAPI" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/main.py && \
      # Check health endpoint
      grep -q "@app.get.*health" /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/main.py && \
      echo "PASS" || echo "FAIL"
    </automated>
  </verify>
  <done>
    - src/app/main.py updated to import models and db
    - Lifespan event calls create_db_tables() on startup
    - FastAPI app configured with title, description, version
    - Health check endpoint exists at /health
    - Root endpoint exists at /
    - App can be started with `uv run uvicorn src.app.main:app --reload`
  </done>
</task>

<task type="auto">
  <name>Task 5: Verify project structure and test basic app startup</name>
  <files>
    src/app/__init__.py
  </files>
  <read_first>
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/pyproject.toml (verify deps installed)
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/main.py (verify imports work)
    - /Users/juanjavierdonoso/Ai Agency/projects/hr-recruitment-ai/src/app/db.py (verify db logic)
  </read_first>
  <action>
1. Create empty src/app/__init__.py (or with version if desired):
   ```python
   """HR Recruitment AI FastAPI application"""
   __version__ = "0.1.0"
   ```

2. Test project structure:
   - Run: `cd /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai && uv run python -c "from src.app.main import app; print('App imports successfully')"`
   - This checks all imports resolve without error

3. Test database initialization:
   - Run: `uv run python -c "from src.app.db import create_db_tables; create_db_tables(); print('Database tables created')"`
   - This verifies SQLModel can create tables

4. Verify file structure exists:
   - Check that src/app/main.py, src/app/db.py, src/app/models.py all exist
   - Check that pyproject.toml has all required deps
  </action>
  <verify>
    <automated>
      # Test app imports
      cd /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai && \
      uv run python -c "from src.app.main import app; from src.app.db import engine; from src.app.models import Client, Job, JobStatus; print('SUCCESS')" 2>&1 | grep -q SUCCESS && \
      # Check files exist
      test -f /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/main.py && \
      test -f /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/db.py && \
      test -f /Users/juanjavierdonoso/Ai\ Agency/projects/hr-recruitment-ai/src/app/models.py && \
      echo "PASS" || echo "FAIL"
    </automated>
  </verify>
  <done>
    - src/app/__init__.py exists
    - All modules (main, db, models) can be imported without errors
    - Project structure correct: src/app/{__init__.py, main.py, db.py, models.py}
    - pyproject.toml has all dependencies (FastAPI, SQLModel, uvicorn, pytest)
    - Database layer initialized and ready for API routes in Plan 02
  </done>
</task>

</tasks>

<verification>
After Plan 01 execution:

1. **Project structure:** Verify directory tree shows src/app/{__init__.py, main.py, db.py, models.py}
2. **Test infrastructure:** Verify tests/{__init__.py, conftest.py, test_models.py, test_routes.py} exist
3. **pyproject.toml:** All locked-decision dependencies present (fastapi, sqlmodel, uvicorn, pytest, pytest-asyncio)
4. **pytest configuration:** [tool.pytest.ini_options] with asyncio_mode = "auto"
5. **Models defined:** Client and Job models in models.py with all fields from 01-CONTEXT.md, JobStatus enum
6. **Database ready:** create_db_tables() function exists and is wired into FastAPI lifespan
7. **App startable:** `uv run uvicorn src.app.main:app --reload` should start without errors
8. **Tests runnable:** `uv run pytest tests/ --collect-only` collects test stubs; fixtures available
9. **No runtime errors:** All imports work, models can be instantiated, database file is created on startup
</verification>

<success_criteria>
- [ ] All files created: pyproject.toml, src/app/{main.py, db.py, models.py, __init__.py}, tests/{__init__.py, conftest.py, test_models.py, test_routes.py}, .env.example, .gitignore
- [ ] pyproject.toml has fastapi>=0.111.0, sqlmodel>=0.0.37, uvicorn[standard], pytest, pytest-asyncio
- [ ] pytest configuration in pyproject.toml with [tool.pytest.ini_options] asyncio_mode = "auto"
- [ ] Client model with id, name, created_at
- [ ] Job model with all JOB-01 fields (title, description, seniority, salary_min, salary_max, required_experience_years, client_id)
- [ ] Job model with JOB-02 JSON columns (target_industries, target_company_types)
- [ ] Job model with JOB-03 status field (JobStatus enum with hunting, shortlisting, interviewing, closed)
- [ ] Database engine created with SQLite connection string
- [ ] create_db_tables() wired into FastAPI lifespan event
- [ ] get_session() dependency available for routes
- [ ] App imports without errors and health check endpoint responds
- [ ] conftest.py has db_session fixture for in-memory SQLite testing
- [ ] test_models.py and test_routes.py have stub functions
- [ ] pytest can collect tests: `uv run pytest tests/ --collect-only` runs without error
- [ ] No blocking errors when running app startup

Requirement coverage:
- JOB-01: Job model has title, description, seniority, salary fields ✓
- JOB-02: Job model has target_industries and target_company_types JSON columns ✓
- JOB-03: Job model has status field (JobStatus enum: hunting, shortlisting, interviewing, closed) ✓
- JOB-04: Status tracking field exists for archive functionality ✓
</success_criteria>

<output>
After completion, create `.planning/phases/01-foundation-job-project-setup/01-PLAN-SUMMARY.md`
</output>
