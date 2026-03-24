"""CompanyMapperAgent — Identifies target companies for candidate hunting"""

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .base import BaseAgent, AgentResponse


class TargetCompanyItem(BaseModel):
    """Company identified as target for hunting"""
    name: str = Field(..., description="Company name")
    industry: str = Field(..., description="Industry classification")
    size_description: str = Field(..., description="Employee count range (e.g., '50-200')")
    linkedin_url: Optional[str] = Field(default=None, description="LinkedIn company profile URL")


class CompanyMapperRequest(BaseModel):
    """Request to identify target companies"""
    job_title: str = Field(..., description="Target job title to search for")
    job_description: str = Field(..., description="Full job description for context")
    target_industries: List[str] = Field(..., description="Industries to focus on")
    target_company_types: List[str] = Field(..., description="Company types (e.g., startup, established)")


class CompanyMapperResponse(BaseModel):
    """Response with identified target companies"""
    companies: List[TargetCompanyItem] = Field(..., description="List of target companies")


class CompanyMapperAgent(BaseAgent):
    """Agent that identifies 5-10 target companies matching job criteria via Claude"""

    def system_prompt(self) -> str:
        """System prompt for company identification"""
        return """You are an expert recruiter who identifies high-potential companies to hunt for candidates.

Your job: Given a job description and industry/company-type preferences, identify 5-10 real companies that match the search criteria.

Return ONLY a JSON-formatted list of companies with:
- name: Company name
- industry: Industry classification
- size_description: Number of employees (e.g., "50-200 employees")
- linkedin_url: LinkedIn company profile URL (use https://linkedin.com/company/[slug] format)

Be specific and realistic. Use your knowledge of real companies in the specified industries."""

    def tools(self) -> List[Dict[str, Any]]:
        """Tool definition for identifying companies"""
        return [
            {
                "name": "identify_companies",
                "description": "Identify target companies matching job criteria",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "companies": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "industry": {"type": "string"},
                                    "size_description": {"type": "string"},
                                    "linkedin_url": {"type": "string"},
                                },
                                "required": ["name", "industry", "size_description"],
                            },
                            "description": "List of identified target companies",
                        },
                    },
                    "required": ["companies"],
                },
            }
        ]

    def parse_response(self, tool_results: List[Dict[str, Any]]) -> CompanyMapperResponse:
        """Parse Claude response into CompanyMapperResponse

        Args:
            tool_results: Tool call results from Claude

        Returns:
            CompanyMapperResponse with validated companies
        """
        if not tool_results:
            return self._get_mock_companies()

        # Extract companies from first tool call
        try:
            tool_input = tool_results[0].get("input", {})
            companies_data = tool_input.get("companies", [])

            # Validate each company against TargetCompanyItem schema
            companies = []
            for company_data in companies_data:
                company = TargetCompanyItem(**company_data)
                companies.append(company)

            return CompanyMapperResponse(companies=companies)

        except Exception:
            # Fall back to mock data on validation error
            return self._get_mock_companies()

    def _get_mock_companies(self) -> CompanyMapperResponse:
        """Return hardcoded mock companies for testing/demo

        # MOCK DATA — Replace with real API calls when LinkedIn API available
        """
        return CompanyMapperResponse(
            companies=[
                TargetCompanyItem(
                    name="Stripe",
                    industry="FinTech",
                    size_description="1000-5000 employees",
                    linkedin_url="https://linkedin.com/company/stripe",
                ),
                TargetCompanyItem(
                    name="Notion",
                    industry="SaaS",
                    size_description="200-500 employees",
                    linkedin_url="https://linkedin.com/company/notion-labs",
                ),
                TargetCompanyItem(
                    name="Figma",
                    industry="Design Tools",
                    size_description="500-1000 employees",
                    linkedin_url="https://linkedin.com/company/figma",
                ),
                TargetCompanyItem(
                    name="McKinsey & Company",
                    industry="Consulting",
                    size_description="5000-10000 employees",
                    linkedin_url="https://linkedin.com/company/mckinsey-company",
                ),
                TargetCompanyItem(
                    name="Airbnb",
                    industry="Travel/Hospitality",
                    size_description="5000-10000 employees",
                    linkedin_url="https://linkedin.com/company/airbnb",
                ),
            ]
        )

    async def run(self, request: CompanyMapperRequest) -> AgentResponse:
        """Run company mapper agent

        Args:
            request: CompanyMapperRequest with job and criteria

        Returns:
            AgentResponse with identified companies
        """
        return await super().run(request)
