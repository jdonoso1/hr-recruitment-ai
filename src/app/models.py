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


class HuntingStatus(str, Enum):
    """Hunting session pipeline status"""
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class CandidateStatus(str, Enum):
    """Candidate approval status in hunting process"""
    hunting = "hunting"
    approved = "approved"
    rejected = "rejected"


class OutreachStatus(str, Enum):
    """Outreach message status tracking"""
    pending_review = "pending_review"
    approved = "approved"
    sent = "sent"
    replied = "replied"
    not_interested = "not_interested"
    error = "error"


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


class HuntingSession(SQLModel, table=True):
    """Represents a candidate hunting run for a specific job"""
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id", index=True)
    status: HuntingStatus = Field(default=HuntingStatus.pending, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TargetCompany(SQLModel, table=True):
    """Target companies identified by AI for hunting"""
    id: Optional[int] = Field(default=None, primary_key=True)
    hunting_session_id: int = Field(foreign_key="hunting_session.id", index=True)
    name: str = Field(index=True)
    industry: str
    size_description: str  # e.g., "50-200 employees"
    linkedin_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class Candidate(SQLModel, table=True):
    """Candidate discovered at a target company"""
    id: Optional[int] = Field(default=None, primary_key=True)
    hunting_session_id: int = Field(foreign_key="hunting_session.id", index=True)
    target_company_id: int = Field(foreign_key="target_company.id", index=True)
    name: str = Field(index=True)
    current_title: str
    current_company: str
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    status: CandidateStatus = Field(default=CandidateStatus.hunting, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OutreachDraft(SQLModel, table=True):
    """AI-drafted outreach messages per candidate"""
    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(foreign_key="candidate.id", index=True)
    job_id: int = Field(foreign_key="job.id", index=True)
    linkedin_message: str = Field(max_length=10000)
    email_message: str = Field(max_length=10000)
    status: OutreachStatus = Field(default=OutreachStatus.pending_review, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
