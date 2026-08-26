import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from langgraph.types import interrupt

from app.schemas.tool import ToolExecution
from app.tools.registry import ToolRegistry

from app.core.enums.approval import ApprovalStatus
from app.db.models.approval_request import ApprovalRequestDB
from app.repositories.approval_repository import ApprovalRepository
from app.services.permission_service import PermissionService
from langgraph.errors import GraphInterrupt


logger = logging.getLogger(__name__)


class ToolExecutorNode:

    def __init__(
        self,
        registry: ToolRegistry,
        approval_repository: ApprovalRepository,
        permission_service: PermissionService,
    ):
        self.registry = registry
        self.approval_repository = approval_repository
        self.permission_service = permission_service

    def __call__(
        self,
        state,
    ):

        print(
            ">>>>>> Tool Executor node started"
        )

        tool_name = state.get(
            "tool_name"
        )

        tool_arguments = (
            state.get("tool_arguments")
            or {}
        )

        iteration = state.get(
            "iteration",
            0,
        )

        retry_count = state.get(
            "retry_count",
            0,
        )

        # ==================================================
        # Initialize approval state
        # ==================================================

        state.setdefault(
            "approval_required",
            False,
        )

        state.setdefault(
            "approval_request_id",
            None,
        )

        state.setdefault(
            "approval_status",
            None,
        )

        # ==================================================
        # Validate tool name
        # ==================================================

        if not tool_name:

            error = "Tool name is missing"

            state["tool_result"] = None
            state["tool_error"] = error

            state["retry_count"] = (
                state.get("retry_count", 0)
                + 1
            )

            execution = ToolExecution(
                tool_name="",
                arguments=tool_arguments,
                result=None,
                error=error,
                success=False,
                iteration=iteration,
                retry_count=retry_count,
                started_at=datetime.now(
                    timezone.utc
                ),
                completed_at=datetime.now(
                    timezone.utc
                ),
            )

            state.setdefault(
                "tool_executions",
                [],
            ).append(
                execution.model_dump(
                    mode="json"
                )
            )

            return state

        # ==================================================
        # Get tool
        # ==================================================

        try:

            tool = self.registry.get(
                tool_name
            )

            if tool is None:

                raise ValueError(
                    f"Unknown tool: {tool_name}"
                )

            # ==================================================
            # Permission / approval gate
            # ==================================================

            user_id = state.get(
                "owner_id"
            )

            conversation_id = state.get(
                "conversation_id"
            )

            run_id = state.get(
                "run_id"
            )

            if not run_id:
                raise ValueError(
                    "run_id is missing from agent state"
                )

            approval_request_id = state.get(
                "approval_request_id"
            )

            # --------------------------------------------------
            # Resume existing approval request
            # --------------------------------------------------
            approval = None

            if approval_request_id:

                approval = self.approval_repository.get(approval_request_id)

            if approval is None:

                approval = (self.approval_repository.get_by_run_id(UUID(run_id)))

            if approval is not None:

                # raise ValueError("Approval request no longer exists")

                if str(approval.run_id) != str(run_id):
                    raise ValueError(
                        "Approval request does not belong "
                        "to this agent run"
                )

                # Keep authoritative approved arguments.

                state["approval_request_id"] = approval.id
                state["approval_status"] = approval.status
                
                tool_name = approval.tool_name
                tool_arguments = approval.arguments

                
                state["tool_name"] = tool_name
                state["tool_arguments"] = tool_arguments

                # --------------------------------------------------
                # APPROVED
                # --------------------------------------------------

                if (
                    approval.status
                    == ApprovalStatus.APPROVED.value
                ):

                    state["approval_required"] = False

                    state["approval_status"] = (
                        ApprovalStatus.APPROVED.value
                    )

                    logger.info(
                        "[APPROVAL] Approval accepted "
                        "approval_id=%s tool=%s",
                        approval.id,
                        tool_name,
                    )

                # --------------------------------------------------
                # REJECTED
                # --------------------------------------------------

                elif (
                    approval.status
                    == ApprovalStatus.REJECTED.value
                ):

                    state["approval_required"] = False

                    state["approval_status"] = (
                        ApprovalStatus.REJECTED.value
                    )

                    state["tool_result"] = None

                    state["tool_error"] = (
                        "The requested tool execution "
                        "was rejected by the user."
                    )

                    logger.info(
                        "[APPROVAL] Tool rejected "
                        "approval_id=%s tool=%s",
                        approval.id,
                        tool_name,
                    )

                    return state

                # --------------------------------------------------
                # EXPIRED
                # --------------------------------------------------

                elif (
                    approval.status
                    == ApprovalStatus.EXPIRED.value
                ):

                    state["approval_required"] = False

                    state["approval_status"] = (
                        ApprovalStatus.EXPIRED.value
                    )

                    state["tool_result"] = None

                    state["tool_error"] = (
                        "The approval request has expired."
                    )

                    logger.info(
                        "[APPROVAL] Approval expired "
                        "approval_id=%s tool=%s",
                        approval.id,
                        tool_name,
                    )

                    return state

                # --------------------------------------------------
                # Still pending
                # --------------------------------------------------

                elif approval.status == ApprovalStatus.PENDING.value:
                    state["approval_request_id"] = approval.id

                    state["approval_required"] = True

                    state["approval_status"] = (
                        ApprovalStatus.PENDING.value
                    )

                    interrupt(
                        {
                            "status": "approval_required",
                            "approval_id": str(
                                approval.id
                            ),
                            "tool_name": tool_name,
                            "arguments": tool_arguments,
                            "reason": approval.reason,
                        }
                    )
                
                else:
                    raise ValueError(f"Unknown approval status: "f"{approval.status}")

            # --------------------------------------------------
            # No existing approval request
            # --------------------------------------------------

            else:

                if not self.permission_service.can_execute(
                    user_id,
                    tool,
                ):

                    # --------------------------------------------------
                    # Tool requires human approval
                    # --------------------------------------------------

                    if self.permission_service.requires_approval(
                        tool
                    ):

                        now = datetime.now(
                            timezone.utc
                        )

                        approval = ApprovalRequestDB(
                            conversation_id=conversation_id,
                            run_id=UUID(run_id),
                            # run_id: str | None,
                            user_id=user_id,
                            tool_name=tool_name,
                            arguments=tool_arguments,
                            reason=(
                                f"Tool '{tool_name}' requires "
                                f"human approval before execution."
                            ),
                            status=(
                                ApprovalStatus.PENDING.value
                            ),
                            created_at=now,
                            expires_at=(
                                now
                                + timedelta(minutes=10)
                            ),
                        )

                        approval = (
                            self.approval_repository.create(
                                approval
                            )
                        )

                        state["approval_required"] = True

                        state["approval_request_id"] = (
                            approval.id
                        )

                        state["approval_status"] = (
                            ApprovalStatus.PENDING.value
                        )

                        # IMPORTANT:
                        # Preserve exact action being approved.
                        state["tool_name"] = (
                            tool_name
                        )

                        state["tool_arguments"] = (
                            tool_arguments
                        )

                        logger.info(
                            "[APPROVAL] Approval required "
                            "approval_id=%s tool=%s run_id=%s",
                            approval.id,
                            tool_name,
                            run_id,
                        )

                        interrupt(
                            {
                                "status": "approval_required",
                                "approval_id": str(
                                    approval.id
                                ),
                                "tool_name": tool_name,
                                "arguments": tool_arguments,
                                "reason": approval.reason,
                            }
                        )

            # ==================================================
            # Actual tool execution
            # ==================================================
            #
            # We only reach here when:
            #
            # LOW/MEDIUM tool
            #
            # OR
            #
            # HIGH/CRITICAL tool that was approved.
            #
            # ==================================================

            state["tool_call_count"] = (
                state.get("tool_call_count", 0)
                + 1
            )

            logger.info(
                "[TOOL] Executing tool=%s "
                "arguments=%s iteration=%s retry=%s "
                "tool_call_count=%s",
                tool_name,
                tool_arguments,
                iteration,
                retry_count,
                state["tool_call_count"],
            )

            execution = ToolExecution(
                tool_name=tool_name,
                arguments=tool_arguments,
                iteration=iteration,
                retry_count=retry_count,
                started_at=datetime.now(
                    timezone.utc
                ),
            )

            # --------------------------------------------------
            # Execute
            # --------------------------------------------------

            result = tool.execute(
                tool_arguments
            )

            logger.info(
                "[TOOL] Result tool=%s result=%s",
                tool_name,
                result,
            )

            state["tool_result"] = result
            state["tool_error"] = None

            # --------------------------------------------------
            # Web search state
            # --------------------------------------------------

            if tool_name == "web_search":

                state["web_results"] = (
                    result.get(
                        "results",
                        [],
                    )
                )

            else:

                state["web_results"] = []

            execution.result = result
            execution.error = None
            execution.success = True

            execution.completed_at = (
                datetime.now(
                    timezone.utc
                )
            )

            state.setdefault(
                "tool_executions",
                [],
            ).append(
                execution.model_dump(
                    mode="json"
                )
            )

            return state

        # ==================================================
        # Tool failure
        # ==================================================

        except GraphInterrupt:
            # IMPORTANT:
            # LangGraph interrupt() is not a tool failure.
            # It intentionally pauses the graph.
            #
            # DO NOT:
            # - increment retry_count
            # - set tool_error
            # - create a failed ToolExecution
            # - return normally
            #
            # Re-raise so LangGraph can pause execution.
            logger.info(
                "[APPROVAL] Graph interrupted waiting "
                "for human approval. tool=%s",
                tool_name,
            )

            raise

        except Exception as exc:

            logger.exception(
                "[TOOL] Tool execution failed: %s",
                exc,
            )

            state["tool_result"] = None
            state["tool_error"] = str(exc)

            state["web_results"] = []

            state["retry_count"] = (
                state.get("retry_count", 0)
                + 1
            )

            execution = ToolExecution(
                tool_name=tool_name,
                arguments=tool_arguments,
                result=None,
                error=str(exc),
                success=False,
                iteration=iteration,
                retry_count=retry_count,
                started_at=datetime.now(
                    timezone.utc
                ),
                completed_at=datetime.now(
                    timezone.utc
                ),
            )

            state.setdefault(
                "tool_executions",
                [],
            ).append(
                execution.model_dump(
                    mode="json"
                )
            )

            return state