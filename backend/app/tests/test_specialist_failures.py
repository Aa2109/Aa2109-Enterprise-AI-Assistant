from app.agents.nodes.responder import ResponderNode
from app.agents.specialists.research_agent import ResearchAgent
from app.agents.supervisor import Supervisor
from app.schemas.agents_schema import AgentName, RoutingDecision
from app.security.models import Role, UserContext
from app.security.rbac import permissions_for_role


QUESTION = (
    "Compare our internal authentication architecture with the latest "
    "industry recommendations."
)


def make_user(role: Role) -> UserContext:
    return UserContext(
        user_id="00000000-0000-0000-0000-000000000001",
        role=role,
        permissions=permissions_for_role(role),
    )


class FailingSearchTool:
    def execute(self, arguments):
        raise RuntimeError("search service unavailable")


class RetryResearchLLM:
    def generate_structured(self, **kwargs):
        return RoutingDecision(
            agents=[AgentName.RESEARCH],
            reasoning="retry research",
            done=False,
        )


class ResponderLLM:
    def __init__(self):
        self.user_prompt = None

    def generate(self, *, system_prompt, user_prompt):
        self.user_prompt = user_prompt
        return "partial specialist synthesis"


class UnexpectedResponderLLM:
    def generate(self, **kwargs):
        raise AssertionError("all-specialist failure should be deterministic")


def test_research_failure_is_returned_as_structured_result():
    state = {
        "question": QUESTION,
        "user_context": make_user(Role.ANALYST),
    }

    result = ResearchAgent(FailingSearchTool())(state)

    failure = result["agent_results"]["research"]
    assert failure["agent"] == "research"
    assert failure["success"] is False
    assert failure["content"] == ""
    # PR-28 — the failure is structured and non-sensitive: the raw
    # exception message ("search service unavailable") is intentionally
    # NOT surfaced to the user.
    assert failure["metadata"]["reason"] == "service_unavailable"
    assert "search service unavailable" not in failure["error"]
    assert result["research_results"] == [failure]


def test_supervisor_does_not_retry_failed_research_agent():
    state = {
        "question": QUESTION,
        "agent_step": 1,
        "pending_agents": [],
        "agent_results": {
            "research": {
                "agent": "research",
                "success": False,
                "content": "",
                "metadata": {},
                "error": "search service unavailable",
            }
        },
    }

    result = Supervisor(RetryResearchLLM())(state)

    assert result["selected_agents"] == []
    assert result["pending_agents"] == []
    assert result["done"] is True
    assert result["supervisor_done"] is True
    assert "failures" in result["supervisor_reason"]


def test_responder_synthesizes_partial_success_and_safe_failure_summary():
    llm = ResponderLLM()
    state = {
        "question": QUESTION,
        "agent_results": {
            "rag": {
                "agent": "rag",
                "success": True,
                "content": "Internal authentication evidence",
                "metadata": {"result_count": 2},
            },
            "research": {
                "agent": "research",
                "success": False,
                "content": "",
                "metadata": {},
                "error": "secret stack trace and credentials",
            },
        },
    }

    result = ResponderNode(llm, context_builder=None)(state)

    assert result["answer"] == "partial specialist synthesis"
    assert "rag" in llm.user_prompt
    assert "external research was unavailable" in llm.user_prompt
    assert "secret stack trace" not in llm.user_prompt


def test_responder_handles_all_specialist_failures_without_llm():
    state = {
        "question": QUESTION,
        "agent_results": {
            "research": {
                "agent": "research",
                "success": False,
                "content": "",
                "metadata": {},
                "error": "secret stack trace",
            }
        },
    }

    result = ResponderNode(
        UnexpectedResponderLLM(),
        context_builder=None,
    )(state)

    assert "research" in result["answer"]
    assert "secret stack trace" not in result["answer"]