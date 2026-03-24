"""BaseAgent — Abstract base class for all AI agents using Anthropic SDK"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import anthropic


class AgentResponse(BaseModel):
    """Standard response format for all agents"""
    status: str = Field(..., description="'success' or 'error'")
    data: Optional[Any] = Field(default=None, description="Structured response data")
    error: Optional[str] = Field(default=None, description="Error message if status='error'")


class BaseAgent(ABC):
    """Abstract base class for agents using Anthropic SDK with async function calling"""

    def __init__(self, model: str = "claude-haiku-4-5"):
        """Initialize agent with Anthropic client

        Args:
            model: Claude model to use (default: claude-haiku-4-5 for cost efficiency)
        """
        self.model = model
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.client = anthropic.AsyncClient(api_key=api_key)

    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this agent

        Returns:
            System prompt string that instructs Claude on the agent's role and task
        """
        pass

    @abstractmethod
    def tools(self) -> List[Dict[str, Any]]:
        """Return list of tool definitions for this agent

        Returns:
            List of tool definitions in OpenAPI/JSON schema format
        """
        pass

    @abstractmethod
    def parse_response(self, tool_results: List[Dict[str, Any]]) -> Any:
        """Parse Claude tool response into domain model

        Args:
            tool_results: List of tool call results from Claude

        Returns:
            Parsed response as domain-specific Pydantic model
        """
        pass

    async def run(self, request: BaseModel) -> AgentResponse:
        """Run the agent with a request

        Args:
            request: Request as Pydantic model

        Returns:
            AgentResponse with status, data, and optional error
        """
        try:
            # Build messages for Claude
            user_message = self._build_user_message(request)

            # Call Claude API with tools
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

        except anthropic.APIError as e:
            # Gracefully handle API errors without re-raising
            return AgentResponse(
                status="error",
                error=f"API Error: {str(e)}"
            )
        except Exception as e:
            # Catch other exceptions
            return AgentResponse(
                status="error",
                error=f"Agent Error: {str(e)}"
            )

    def _build_user_message(self, request: BaseModel) -> str:
        """Build user message from request

        Args:
            request: Request Pydantic model

        Returns:
            User message string
        """
        return request.model_dump_json()
