"""Tests for OutreachDrafterAgent (Phase 2 Plan 03). The Claude API is always mocked."""

from unittest.mock import AsyncMock, MagicMock

import anthropic
import httpx
import pytest
from pydantic import ValidationError

from src.app.agents.base import AgentResponse
from src.app.agents.outreach_drafter import (
    EMAIL_MAX_CHARS,
    LINKEDIN_MAX_CHARS,
    TEMPLATE_NOTE,
    TRIM_NOTE,
    CandidateSummary,
    JobSummary,
    OutreachDrafterAgent,
    OutreachDrafterRequest,
    OutreachDrafterResponse,
    TargetCompanySummary,
    build_template_draft,
    trim_message,
)


@pytest.fixture
def outreach_request():
    return OutreachDrafterRequest(
        job=JobSummary(
            id=1,
            title="Senior Python Engineer",
            description="Build scalable systems with Python and FastAPI",
            seniority="Senior",
            salary_min=150000,
            salary_max=200000,
            required_experience_years=5,
        ),
        candidate=CandidateSummary(
            name="Alice Johnson",
            current_title="Senior Engineer",
            current_company="Tech Startup Inc",
            linkedin_url="https://linkedin.com/in/alice-johnson",
        ),
        company=TargetCompanySummary(
            name="Tech Startup Inc",
            industry="Technology",
            size_description="50-200 employees",
        ),
    )


def _tool_response(tool_input):
    """Build a fake Messages API response containing one tool_use block."""
    block = MagicMock()
    block.type = "tool_use"
    block.id = "toolu_1"
    block.name = "generate_outreach_messages"
    block.input = tool_input
    response = MagicMock()
    response.content = [block]
    return response


def _agent_with_response(response):
    agent = OutreachDrafterAgent()
    agent.client.messages.create = AsyncMock(return_value=response)
    return agent


class TestAgentDefinition:
    def test_agent_initializes_async_client(self):
        agent = OutreachDrafterAgent()
        assert isinstance(agent.client, anthropic.AsyncClient)

    def test_tool_schema_requires_both_messages(self):
        tool = OutreachDrafterAgent().tools()[0]
        assert tool["name"] == "generate_outreach_messages"
        assert set(tool["input_schema"]["required"]) == {"linkedin_message", "email_message"}

    def test_system_prompt_sets_length_limits(self):
        prompt = OutreachDrafterAgent().system_prompt()
        assert str(LINKEDIN_MAX_CHARS) in prompt
        assert str(EMAIL_MAX_CHARS) in prompt

    def test_user_message_includes_job_and_candidate_context(self, outreach_request):
        message = OutreachDrafterAgent()._build_user_message(outreach_request)
        for expected in ["Alice Johnson", "Senior Engineer", "Tech Startup Inc",
                         "Senior Python Engineer", "FastAPI", "5+ years", "$150,000"]:
            assert expected in message


class TestRun:
    async def test_generates_both_messages(self, outreach_request):
        agent = _agent_with_response(_tool_response({
            "linkedin_message": "Hi Alice, your work as Senior Engineer at Tech Startup Inc caught my eye. Open to exploring?",
            "email_message": "Subject: Senior Python Engineer\n\nHi Alice,\n\nInterested in a quick chat?",
        }))

        result = await agent.run(outreach_request)

        assert result.status == "success"
        assert isinstance(result.data, OutreachDrafterResponse)
        assert "Alice" in result.data.linkedin_message
        assert "Tech Startup Inc" in result.data.linkedin_message
        assert result.data.email_message.startswith("Subject:")

        # The request context reached the API call
        call = agent.client.messages.create.call_args.kwargs
        assert "Alice Johnson" in call["messages"][0]["content"]
        assert call["tools"][0]["name"] == "generate_outreach_messages"

    async def test_overlong_messages_are_trimmed(self, outreach_request):
        agent = _agent_with_response(_tool_response({
            "linkedin_message": "a" * 5000,
            "email_message": "b" * 5000,
        }))

        result = await agent.run(outreach_request)

        assert result.status == "success"
        assert len(result.data.linkedin_message) <= LINKEDIN_MAX_CHARS
        assert len(result.data.email_message) <= EMAIL_MAX_CHARS
        assert result.data.linkedin_message.endswith(TRIM_NOTE)
        assert result.data.email_message.endswith(TRIM_NOTE)

    async def test_missing_field_returns_error(self, outreach_request):
        agent = _agent_with_response(_tool_response({"linkedin_message": "Hi"}))
        result = await agent.run(outreach_request)
        assert result.status == "error"
        assert result.error

    async def test_no_tool_call_returns_error(self, outreach_request):
        response = MagicMock()
        response.content = []
        result = await _agent_with_response(response).run(outreach_request)
        assert result.status == "error"

    async def test_api_error_returns_error_response(self, outreach_request):
        agent = OutreachDrafterAgent()
        agent.client.messages.create = AsyncMock(side_effect=anthropic.APIConnectionError(
            request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        ))

        result = await agent.run(outreach_request)

        assert isinstance(result, AgentResponse)
        assert result.status == "error"
        assert "API Error" in result.error


class TestParseResponse:
    def test_rejects_missing_fields(self):
        with pytest.raises(ValidationError):
            OutreachDrafterAgent().parse_response([{"input": {"email_message": "Hi"}}])

    def test_rejects_empty_messages(self):
        with pytest.raises(ValidationError):
            OutreachDrafterAgent().parse_response(
                [{"input": {"linkedin_message": "", "email_message": "Hi"}}]
            )


class TestHelpers:
    def test_trim_message_leaves_short_messages_alone(self):
        assert trim_message("  hello  ", 100) == "hello"

    def test_trim_message_respects_limit(self):
        trimmed = trim_message("x" * 1500, 1000)
        assert len(trimmed) <= 1000
        assert trimmed.endswith(TRIM_NOTE)

    def test_template_draft_is_personalized_and_labelled(self, outreach_request):
        draft = build_template_draft(outreach_request)

        for message in (draft.linkedin_message, draft.email_message):
            assert "Alice" in message
            assert "Tech Startup Inc" in message
            assert "Senior Python Engineer" in message
            assert TEMPLATE_NOTE in message
        assert "$150,000–$200,000" in draft.email_message
        assert len(draft.linkedin_message) <= LINKEDIN_MAX_CHARS
        assert len(draft.email_message) <= EMAIL_MAX_CHARS

    def test_template_draft_omits_missing_salary(self, outreach_request):
        outreach_request.job.salary_min = None
        outreach_request.job.salary_max = None
        assert "$" not in build_template_draft(outreach_request).email_message

    def test_template_draft_does_not_repeat_seniority(self, outreach_request):
        # Title "Senior Python Engineer" already contains seniority "Senior"
        draft = build_template_draft(outreach_request)
        assert "Senior Senior" not in draft.linkedin_message
        assert "Senior Senior" not in draft.email_message

    def test_template_draft_adds_seniority_when_missing_from_title(self, outreach_request):
        outreach_request.job.title = "Python Engineer"
        assert "Senior Python Engineer" in build_template_draft(outreach_request).linkedin_message
