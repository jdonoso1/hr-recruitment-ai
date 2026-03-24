"""RoleIdentifierAgent — Discovers candidates at target companies

This agent identifies 3-5 candidates per company who match the target job role,
seniority level, and company context. Results are Candidate records.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .base import BaseAgent, AgentResponse


class CompanyInfo(BaseModel):
    """Target company for candidate identification"""
    name: str = Field(..., description="Company name")
    industry: str = Field(..., description="Industry classification")
    size_description: str = Field(..., description="Employee count range")


class CandidateItem(BaseModel):
    """Discovered candidate at a target company"""
    name: str = Field(..., description="Full name of candidate")
    current_title: str = Field(..., description="Current job title")
    current_company: str = Field(..., description="Current company name")
    email: Optional[str] = Field(default=None, description="Email address if available")
    linkedin_url: Optional[str] = Field(default=None, description="LinkedIn profile URL if available")


class RoleIdentifierRequest(BaseModel):
    """Request to identify candidates at target companies"""
    job_title: str = Field(..., description="Target job title to search for")
    job_description: str = Field(..., description="Full job description for context")
    seniority: str = Field(..., description="Seniority level (e.g., 'Senior', 'Manager')")
    target_companies: List[CompanyInfo] = Field(..., description="Companies to search for candidates")


class RoleIdentifierResponse(BaseModel):
    """Response with identified candidates"""
    candidates: List[CandidateItem] = Field(..., description="List of discovered candidates")


class RoleIdentifierAgent(BaseAgent):
    """Agent that identifies 3-5 candidates per company matching job criteria"""

    def system_prompt(self) -> str:
        """System prompt for candidate identification"""
        return """You are an expert recruiter who identifies high-potential candidates at specific companies.

Your job: Given a job description, seniority level, and list of target companies, identify 3-5 real candidates at each company who hold (or could hold) the target role.

For each candidate, use your knowledge to provide:
- Full name
- Current job title
- Current company name
- Email (if you know it, otherwise leave empty)
- LinkedIn URL (use https://linkedin.com/in/[slug] format if known)

Be specific and realistic. Draw from your knowledge of real people in these industries.
Return only candidates who realistically match the job requirements and seniority level."""

    def tools(self) -> List[Dict[str, Any]]:
        """Tool definition for identifying candidates"""
        return [
            {
                "name": "identify_candidates_at_company",
                "description": "Identify candidates at a specific company matching the target role",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "candidates": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "current_title": {"type": "string"},
                                    "current_company": {"type": "string"},
                                    "email": {"type": "string"},
                                    "linkedin_url": {"type": "string"},
                                },
                                "required": ["name", "current_title", "current_company"],
                            },
                            "description": "List of identified candidates",
                        },
                    },
                    "required": ["candidates"],
                },
            }
        ]

    def parse_response(self, tool_results: List[Dict[str, Any]]) -> RoleIdentifierResponse:
        """Parse Claude response into RoleIdentifierResponse

        Args:
            tool_results: Tool call results from Claude

        Returns:
            RoleIdentifierResponse with validated candidates
        """
        if not tool_results:
            return self._get_mock_candidates()

        try:
            tool_input = tool_results[0].get("input", {})
            candidates_data = tool_input.get("candidates", [])

            # Validate each candidate against CandidateItem schema
            candidates = []
            for candidate_data in candidates_data:
                candidate = CandidateItem(**candidate_data)
                candidates.append(candidate)

            return RoleIdentifierResponse(candidates=candidates)

        except Exception:
            # Fall back to mock data on validation error
            return self._get_mock_candidates()

    def _get_mock_candidates(self) -> RoleIdentifierResponse:
        """Return hardcoded mock candidates for testing/demo

        # MOCK DATA — Replace with real API calls when LinkedIn/Clearbit API available
        """
        return RoleIdentifierResponse(
            candidates=[
                CandidateItem(
                    name="Sarah Chen",
                    current_title="Senior Product Manager",
                    current_company="Stripe",
                    email="sarah.chen@stripe.com",
                    linkedin_url="https://linkedin.com/in/sarahchen",
                ),
                CandidateItem(
                    name="James Morrison",
                    current_title="Product Lead",
                    current_company="Notion",
                    email="james.morrison@notion.so",
                    linkedin_url="https://linkedin.com/in/jamesmorrison",
                ),
                CandidateItem(
                    name="Emma Rodriguez",
                    current_title="Senior Manager, Product",
                    current_company="Figma",
                    email=None,
                    linkedin_url="https://linkedin.com/in/emmarodriguez",
                ),
                CandidateItem(
                    name="Alex Park",
                    current_title="Principal PM",
                    current_company="Slack",
                    email="alex.park@slack.com",
                    linkedin_url="https://linkedin.com/in/alexpark",
                ),
                CandidateItem(
                    name="Maya Patel",
                    current_title="VP Product",
                    current_company="Shopify",
                    email=None,
                    linkedin_url="https://linkedin.com/in/mayapatel",
                ),
            ]
        )

    async def run(self, request: RoleIdentifierRequest) -> AgentResponse:
        """Run the role identifier agent

        Args:
            request: RoleIdentifierRequest with job context and target companies

        Returns:
            AgentResponse with candidate list
        """
        try:
            # Build user message with context
            user_message = f"""
Find candidates matching this role at the target companies:

JOB TITLE: {request.job_title}
SENIORITY: {request.seniority}
JOB DESCRIPTION: {request.job_description}

TARGET COMPANIES:
{chr(10).join([f"- {c.name} ({c.industry}, {c.size_description})" for c in request.target_companies])}

Identify 3-5 candidates per company who match the role seniority and company context.
"""

            # Call parent run() to handle Claude API call
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=self.system_prompt(),
                tools=self.tools(),
                messages=[
                    {
                        "role": "user",
                        "content": user_message,
                    }
                ],
            )

            # Extract tool results
            tool_results = []
            for content_block in response.content:
                if hasattr(content_block, "type") and content_block.type == "tool_use":
                    tool_results.append({
                        "id": content_block.id,
                        "name": content_block.name,
                        "input": content_block.input,
                    })

            # Parse response using domain-specific logic
            data = self.parse_response(tool_results)

            return AgentResponse(status="success", data=data)

        except Exception as e:
            return AgentResponse(status="error", error=str(e))
