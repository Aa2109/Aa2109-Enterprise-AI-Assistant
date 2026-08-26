from app.tools.base import ToolRisk


class PermissionService:

    def can_execute(
        self,
        user_id,
        tool,
    ) -> bool:

        return tool.risk_level in {
            ToolRisk.LOW,
            ToolRisk.MEDIUM,
        }

    def requires_approval(
        self,
        tool,
    ) -> bool:

        return tool.requires_approval