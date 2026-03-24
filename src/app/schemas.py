from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from .models import JobStatus


# Client schemas
class ClientCreate(BaseModel):
    """Request schema for creating a client"""
    name: str = Field(..., min_length=1, max_length=200)


class ClientRead(BaseModel):
    """Response schema for client"""
    id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True  # Allow Pydantic to read from SQLModel instances


# Job schemas
class JobCreate(BaseModel):
    """Request schema for creating a new job"""
    client_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=10)
    seniority: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    required_experience_years: Optional[int] = None
    target_industries: List[str] = Field(default=[])
    target_company_types: List[str] = Field(default=[])


class JobUpdate(BaseModel):
    """Request schema for updating a job"""
    title: Optional[str] = None
    description: Optional[str] = None
    seniority: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    required_experience_years: Optional[int] = None
    target_industries: Optional[List[str]] = None
    target_company_types: Optional[List[str]] = None


class JobRead(BaseModel):
    """Response schema for job detail"""
    id: int
    client_id: int
    title: str
    description: str
    seniority: str
    salary_min: Optional[int]
    salary_max: Optional[int]
    required_experience_years: Optional[int]
    target_industries: List[str]
    target_company_types: List[str]
    status: JobStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobListItem(BaseModel):
    """Response schema for job in list (includes related client data)"""
    id: int
    title: str
    client_id: int
    status: JobStatus
    created_at: datetime
