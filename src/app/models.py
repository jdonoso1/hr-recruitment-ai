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
