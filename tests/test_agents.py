"""Tests for agent infrastructure and CompanyMapperAgent"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError

from src.app.agents.base import BaseAgent, AgentResponse
from src.app.agents.company_mapper import (
    CompanyMapperAgent,
    CompanyMapperRequest,
    CompanyMapperResponse,
    TargetCompanyItem,
)


class MockAgent(BaseAgent):
    """Concrete mock agent for testing BaseAgent"""

    def system_prompt(self) -> str:
        return "Test system prompt"

    def tools(self):
        return []

    def parse_response(self, tool_results):
        return {"test": "data"}


class TestBaseAgentInitialization:
    """Test BaseAgent initialization"""

    def test_base_agent_initializes_with_default_model(self):
        """Verify AsyncClient is created with default model"""
        agent = MockAgent()
        assert agent.model == "claude-haiku-4-5"
        assert agent.client is not None

    def test_base_agent_initializes_with_custom_model(self):
        """Verify custom model is set correctly"""
        agent = MockAgent(model="claude-opus-4")
        assert agent.model == "claude-opus-4"

    def test_base_agent_reads_api_key_from_env(self, monkeypatch):
        """Verify API key is read from ANTHROPIC_API_KEY env var"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-123")
        # AsyncClient initialization would use the env var
        agent = MockAgent()
        assert agent.client is not None


class TestCompanyMapperRequestValidation:
    """Test CompanyMapperRequest Pydantic validation"""

    def test_company_mapper_request_with_all_fields(self):
        """Verify request accepts all required fields"""
        request = CompanyMapperRequest(
            job_title="Senior Python Engineer",
            job_description="Build scalable systems",
            target_industries=["Technology", "Finance"],
            target_company_types=["Startup", "Scale-up"],
        )
        assert request.job_title == "Senior Python Engineer"
        assert len(request.target_industries) == 2

    def test_company_mapper_request_missing_field_raises_validation_error(self):
        """Verify missing required field raises ValidationError"""
        with pytest.raises(ValidationError):
            CompanyMapperRequest(
                job_title="Senior Python Engineer",
                # Missing job_description
                target_industries=["Technology"],
                target_company_types=["Startup"],
            )


class TestTargetCompanyItemValidation:
    """Test TargetCompanyItem Pydantic model"""

    def test_target_company_item_with_all_fields(self):
        """Verify company item with all fields"""
        company = TargetCompanyItem(
            name="Stripe",
            industry="FinTech",
            size_description="1000-5000 employees",
            linkedin_url="https://linkedin.com/company/stripe",
        )
        assert company.name == "Stripe"
        assert company.linkedin_url is not None

    def test_target_company_item_without_linkedin_url(self):
        """Verify company item without optional LinkedIn URL"""
        company = TargetCompanyItem(
            name="Acme Corp",
            industry="Technology",
            size_description="50-200 employees",
        )
        assert company.linkedin_url is None
        assert company.name == "Acme Corp"


class TestCompanyMapperAgent:
    """Test CompanyMapperAgent"""

    def test_company_mapper_agent_inherits_from_base_agent(self):
        """Verify CompanyMapperAgent is a BaseAgent"""
        agent = CompanyMapperAgent()
        assert isinstance(agent, BaseAgent)

    def test_system_prompt_is_defined(self):
        """Verify system prompt is provided"""
        agent = CompanyMapperAgent()
        prompt = agent.system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "company" in prompt.lower() or "hunt" in prompt.lower()

    def test_tools_returns_tool_definitions(self):
        """Verify tools() returns proper tool definitions"""
        agent = CompanyMapperAgent()
        tools = agent.tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
        assert tools[0]["name"] == "identify_companies"
        assert "input_schema" in tools[0]

    def test_parse_response_with_valid_tool_results(self):
        """Verify parse_response handles valid tool results"""
        agent = CompanyMapperAgent()
        tool_results = [
            {
                "input": {
                    "companies": [
                        {
                            "name": "Tech Startup",
                            "industry": "Technology",
                            "size_description": "50-100 employees",
                            "linkedin_url": "https://linkedin.com/company/tech-startup",
                        }
                    ]
                }
            }
        ]
        response = agent.parse_response(tool_results)
        assert isinstance(response, CompanyMapperResponse)
        assert len(response.companies) == 1
        assert response.companies[0].name == "Tech Startup"

    def test_parse_response_with_empty_tool_results_returns_mock(self):
        """Verify parse_response returns mock companies when tool results empty"""
        agent = CompanyMapperAgent()
        response = agent.parse_response([])
        assert isinstance(response, CompanyMapperResponse)
        assert len(response.companies) >= 5
        assert all(isinstance(c, TargetCompanyItem) for c in response.companies)

    def test_parse_response_with_invalid_data_returns_mock(self):
        """Verify parse_response returns mock when data is invalid"""
        agent = CompanyMapperAgent()
        tool_results = [{"input": {"companies": [{"name": "Invalid"}]}}]  # Missing required fields
        response = agent.parse_response(tool_results)
        assert isinstance(response, CompanyMapperResponse)
        assert len(response.companies) >= 5

    def test_mock_companies_have_all_fields(self):
        """Verify mock companies include all required fields"""
        agent = CompanyMapperAgent()
        response = agent._get_mock_companies()
        for company in response.companies:
            assert company.name
            assert company.industry
            assert company.size_description
            # LinkedIn URL is optional but provided in mocks
            assert company.linkedin_url


@pytest.mark.asyncio
async def test_company_mapper_agent_run_with_mock_api():
    """Test CompanyMapperAgent.run() with mocked API (doesn't call Claude)"""
    agent = CompanyMapperAgent()

    # Mock the API call to return tool use
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.type = "tool_use"
    mock_content.id = "tool_123"
    mock_content.name = "identify_companies"
    mock_content.input = {
        "companies": [
            {
                "name": "Stripe",
                "industry": "FinTech",
                "size_description": "1000-5000 employees",
                "linkedin_url": "https://linkedin.com/company/stripe",
            }
        ]
    }
    mock_response.content = [mock_content]

    # Patch the async API call
    with patch.object(agent.client, "messages.create", new_callable=AsyncMock) as mock_api:
        mock_api.return_value = mock_response

        request = CompanyMapperRequest(
            job_title="Senior Python Engineer",
            job_description="Build scalable systems",
            target_industries=["FinTech"],
            target_company_types=["Scale-up"],
        )

        response = await agent.run(request)

        # Verify response structure
        assert response.status == "success"
        assert response.data is not None
        assert isinstance(response.data, CompanyMapperResponse)
        assert len(response.data.companies) > 0

        # Verify API was called
        assert mock_api.called


@pytest.mark.asyncio
async def test_company_mapper_agent_run_with_api_error():
    """Test CompanyMapperAgent.run() handles API errors gracefully"""
    import anthropic

    agent = CompanyMapperAgent()

    # Mock API to raise an error
    with patch.object(agent.client, "messages.create", new_callable=AsyncMock) as mock_api:
        mock_api.side_effect = anthropic.APIError("API rate limit exceeded")

        request = CompanyMapperRequest(
            job_title="Senior Python Engineer",
            job_description="Build scalable systems",
            target_industries=["Technology"],
            target_company_types=["Startup"],
        )

        response = await agent.run(request)

        # Verify error is caught and returned, not re-raised
        assert response.status == "error"
        assert response.error is not None
        assert "API Error" in response.error


@pytest.mark.asyncio
async def test_company_mapper_agent_run_returns_mock_on_no_tools():
    """Test CompanyMapperAgent.run() returns mock companies when no tools called"""
    agent = CompanyMapperAgent()

    # Mock API to return no tool calls
    mock_response = MagicMock()
    mock_response.content = []  # No tool calls

    with patch.object(agent.client, "messages.create", new_callable=AsyncMock) as mock_api:
        mock_api.return_value = mock_response

        request = CompanyMapperRequest(
            job_title="Senior Python Engineer",
            job_description="Build scalable systems",
            target_industries=["Technology"],
            target_company_types=["Startup"],
        )

        response = await agent.run(request)

        # Should return mock companies as fallback
        assert response.status == "success"
        assert isinstance(response.data, CompanyMapperResponse)
        assert len(response.data.companies) >= 5


class TestAgentResponseFormat:
    """Test AgentResponse standard format"""

    def test_agent_response_success(self):
        """Verify successful response format"""
        data = {"key": "value"}
        response = AgentResponse(status="success", data=data)
        assert response.status == "success"
        assert response.data == data
        assert response.error is None

    def test_agent_response_error(self):
        """Verify error response format"""
        response = AgentResponse(status="error", error="Something went wrong")
        assert response.status == "error"
        assert response.error == "Something went wrong"
        assert response.data is None
