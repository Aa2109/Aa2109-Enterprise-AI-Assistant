from app.tools.registry import ToolRegistry
from app.tools.implementations.calculator import CalculatorTool


def create_tool_registry() -> ToolRegistry:
    return ToolRegistry(
        tools=[
            CalculatorTool(),
        ]
    )