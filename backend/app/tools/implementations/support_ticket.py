from typing import Any

from app.tools.base import BaseTool, ToolRisk


class CreateSupportTicketTool(BaseTool):

    @property
    def name(self) -> str:
        return "create_support_ticket"

    @property
    def description(self) -> str:
        return (
            "Creates a support ticket with a title and description."
        )

    @property
    def risk_level(self) -> ToolRisk:
        return ToolRisk.HIGH

    @property
    def requires_approval(self) -> bool:
        return True

    def execute(
        self,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:

        title = arguments.get("title")
        description = arguments.get("description")

        if not title:
            raise ValueError(
                "Support ticket title is required"
            )

        if not description:
            raise ValueError(
                "Support ticket description is required"
            )

        # Mock implementation.
        # Later this can call Jira/ServiceNow.

        return {
            "success": True,
            "ticket_id": "MOCK-001",
            "title": title,
            "description": description,
            "status": "CREATED",
        }