'''from fastapi import Depends

from app.agents.nodes.tool_executor import ToolExecutorNode
from app.dependencies.tools import get_tool_registry


def get_tool_executor_node(
    tool_registry=Depends(get_tool_registry),
):
    return ToolExecutorNode(tool_registry)
'''
from fastapi import Depends

from app.agents.nodes.tool_executor import ToolExecutorNode
from app.dependencies.tools import get_tool_registry
from app.dependencies.approval import get_approval_repository
from app.dependencies.permission import get_permission_service


def get_tool_executor_node(
    tool_registry=Depends(get_tool_registry),
    approval_repository=Depends(get_approval_repository),
    permission_service=Depends(get_permission_service),
):
    return ToolExecutorNode(
        tool_registry,
        approval_repository,
        permission_service,
    )

# Backward-compatible alias for older imports.
# def get_tool_executor(
#     registry=Depends(get_tool_registry),
# ):
#     return get_tool_executor_node(registry)