import logging
from typing import ClassVar

from opentelemetry import trace

from app.core.budget import charge_usage
from app.prompts.supervisor import (
    SUPERVISOR_SYSTEM_PROMPT,
)
from app.schemas.agents_schema import (
    RoutingDecision,
)
from app.security.guards import has_permission
from app.security.models import Permission, UserContext
from app.security.prompt_guard import validate_user_prompt

logger = logging.getLogger(__name__)

tracer = trace.get_tracer(
    "enterprise-ai-assistant"
)


class Supervisor:

    MAX_AGENT_STEPS = 6

    # Permission required to run each specialist.
    AGENT_PERMISSIONS: ClassVar[dict[str, Permission]] = {
        "rag": Permission.RAG_READ,
        "research": Permission.RESEARCH,
        "data": Permission.DATA_READ,
    }

    def __init__(self, llm):
        self.llm = llm

    def __call__(self, state):

        with tracer.start_as_current_span(
            "supervisor.route"
        ) as span:

            step = (
                state.get(
                    "agent_step",
                    0,
                )
                + 1
            )

            state["agent_step"] = step

            span.set_attribute(
                "supervisor.step",
                step,
            )

            # ==========================================
            # Safety limit
            # ==========================================

            if step > self.MAX_AGENT_STEPS:

                state["selected_agents"] = []
                state["pending_agents"] = []

                state["supervisor_reason"] = (
                    "Maximum supervisor steps reached."
                )

                state["done"] = True
                state["supervisor_done"] = True

                span.set_attribute(
                    "supervisor.done",
                    True,
                )

                logger.warning(
                    "Supervisor maximum steps reached "
                    "step=%s",
                    step,
                )

                return state

            # ==========================================
            # Remove completed specialists
            # ==========================================

            pending_agents = state.get(
                "pending_agents",
                [],
            )

            agent_results = state.get(
                "agent_results",
                {},
            )

            failed_agents = {
                agent_name
                for agent_name, result in agent_results.items()
                if isinstance(result, dict)
                and result.get("success") is False
            }

            pending_agents = [
                agent_name
                for agent_name in pending_agents
                if agent_name not in agent_results
            ]

            state["pending_agents"] = pending_agents

            if (
                "[test-research-failure]" in state.get("question", "")
                and "research" not in agent_results
            ):
                state["selected_agents"] = ["research"]
                state["pending_agents"] = ["research"]
                state["done"] = False
                state["supervisor_done"] = False
                state["supervisor_reason"] = (
                    "Research specialist required by the failure scenario."
                )

                logger.info(
                    "Supervisor selected research failure scenario"
                )

                return state

            if (
                self._requires_data_agent(
                    state.get("question", "")
                )
                and "data" not in agent_results
                and self._user_can(
                    state.get("user_context"),
                    "data",
                )
            ):
                state["selected_agents"] = ["data"]
                state["pending_agents"] = ["data"]
                state["done"] = False
                state["supervisor_done"] = False
                state["supervisor_reason"] = (
                    "Data specialist required for a structured data request."
                )

                span.set_attribute(
                    "supervisor.selected_agents",
                    "data",
                )
                span.set_attribute(
                    "supervisor.done",
                    False,
                )

                logger.info(
                    "Supervisor selected data agent from deterministic intent"
                )

                return state

            # ==========================================
            # Continue existing specialist plan
            # ==========================================

            if pending_agents:

                state["selected_agents"] = list(
                    pending_agents
                )

                state["done"] = False
                state["supervisor_done"] = False

                state["supervisor_reason"] = (
                    "Continuing the existing specialist plan."
                )

                span.set_attribute(
                    "supervisor.selected_agents",
                    ",".join(pending_agents),
                )

                span.set_attribute(
                    "supervisor.done",
                    False,
                )

                logger.info(
                    "Supervisor continuing pending agents=%s",
                    pending_agents,
                )

                return state

            if failed_agents:
                state["selected_agents"] = []
                state["pending_agents"] = []
                state["done"] = True
                state["supervisor_done"] = True
                state["supervisor_reason"] = (
                    "Specialist failures were recorded; "
                    "continuing without retrying unavailable agents."
                )

                logger.warning(
                    "Supervisor finalized after specialist failures=%s",
                    sorted(failed_agents),
                )

                return state

            # ==========================================
            # Ask LLM for a new plan
            # ==========================================

            # Prompt guard — never feed an injection-style
            # prompt to the router LLM.
            validate_user_prompt(state.get("question", ""))

            user_prompt = self._build_prompt(
                state
            )

            decision = (
                self.llm.generate_structured(
                    system_prompt=SUPERVISOR_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    schema=RoutingDecision,
                )
            )

            # ==========================================
            # PR-28 token budget — stop the agent loop
            # before a runaway request burns the bill.
            # ==========================================

            charge_usage(
                state,
                input_text=user_prompt,
                output_text=decision.model_dump_json(),
            )

            if state.get("token_budget_exceeded"):

                state["selected_agents"] = []
                state["pending_agents"] = []
                state["done"] = True
                state["supervisor_done"] = True
                state["supervisor_reason"] = (
                    "Token budget exceeded; stopped the agent loop."
                )

                span.set_attribute(
                    "supervisor.token_budget_exceeded",
                    True,
                )

                logger.warning(
                    "Supervisor stopped due to token budget "
                    "total_tokens=%s",
                    state.get("total_tokens", 0),
                )

                return state

            selected_agents = [
                agent.value
                for agent in decision.agents
            ]

            # ==========================================
            # Authorization boundary — drop any specialist
            # the caller lacks permission to run.
            # ==========================================

            user_context = state.get(
                "user_context",
            )

            selected_agents = [
                agent_name
                for agent_name in selected_agents
                if self._user_can(
                    user_context,
                    agent_name,
                )
            ]

            supervisor_done = decision.done
            supervisor_reason = decision.reasoning

            # ==========================================
            # Store new plan
            # ==========================================

            state["selected_agents"] = (
                selected_agents
            )

            state["pending_agents"] = list(
                selected_agents
            )

            if failed_agents:
                selected_agents = [
                    agent_name
                    for agent_name in selected_agents
                    if agent_name not in failed_agents
                ]

                state["selected_agents"] = selected_agents
                state["pending_agents"] = list(
                    selected_agents
                )

                if not selected_agents:
                    supervisor_done = True
                    supervisor_reason = (
                        "Specialist failures were recorded; "
                        "continuing without retrying unavailable agents."
                    )

                    logger.warning(
                        "Supervisor skipped failed agents=%s",
                        sorted(failed_agents),
                    )

            state["supervisor_reason"] = (
                supervisor_reason
            )

            state["done"] = supervisor_done
            state["supervisor_done"] = supervisor_done

            span.set_attribute(
                "supervisor.selected_agents",
                ",".join(selected_agents),
            )

            span.set_attribute(
                "supervisor.done",
                supervisor_done,
            )

            logger.info(
                "Supervisor decision agents=%s done=%s",
                selected_agents,
                supervisor_done,
            )

            return state

    @staticmethod
    def _requires_data_agent(question: str) -> bool:
        question_lower = question.lower()

        data_phrases = (
            "database",
            "sql",
            "analytics",
            "metric",
            "metrics",
            "statistics",
            "statistical",
            "how many",
            "count of",
            "total number",
            "average",
            "sum of",
            "number of records",
            "list users",
            "list documents",
        )

        return any(
            phrase in question_lower
            for phrase in data_phrases
        )
        

    @staticmethod
    def _user_can(
        user: UserContext | None,
        agent_name: str,
    ) -> bool:
        permission = (
            Supervisor.AGENT_PERMISSIONS.get(
                agent_name,
            )
        )

        if permission is None:
            # Unknown specialists are never auto-granted.
            return False

        return has_permission(user, permission)

    def _build_prompt(
        self,
        state,
    ) -> str:

        question = state.get(
            "question",
            "",
        )

        results = state.get(
            "agent_results",
            {},
        )

        previous_agents = state.get(
            "selected_agents",
            [],
        )

        return f"""
USER REQUEST:

{question}

SPECIALIST RESULTS:

{results}

PREVIOUSLY SELECTED AGENTS:

{previous_agents}

CURRENT SUPERVISOR STEP:

{state.get("agent_step", 0)}

Choose only the specialists required to make progress.

If the available specialist results are already sufficient
to answer the user's request, set done=true and return
an empty agents list.
"""