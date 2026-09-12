"""PR-30 — tests for the standardized AgentResult contract and the
final-synthesis AI policy layer.

Covers:
- specialists populate real ``content`` + ``sources`` that conform to
  the AgentResult schema
- RAG no-evidence produces a deterministic, non-fabricating answer
- partial synthesis uses only successful evidence with safe failure
  wording, and never leaks raw error text
- all-failed / permission-denied paths stay deterministic (no LLM)
- source collection deduplicates across agents
"""

from uuid import UUID

from app.agents.nodes.responder import ResponderNode
from app.agents.result import result_to_model, validate_result
from app.agents.specialists.data_agent import DataAgent
from app.agents.specialists.rag_agent import RAGAgent
from app.agents.specialists.research_agent import ResearchAgent
from app.agents.synthesis import (
    NO_INTERNAL_DOCUMENT_ANSWER,
    PERMISSION_DENIED_ANSWER,
    SynthesisPolicy,
)
from app.schemas.agents_schema import AgentResult
from app.schemas.search import SearchHit
from app.security.models import Role, UserContext
from app.security.rbac import permissions_for_role

ADMIN = UserContext(
    user_id="00000000-0000-0000-0000-0000000000aa",
    role=Role.ADMIN,
    permissions=permissions_for_role(Role.ADMIN),
)

DOC_ID = UUID("10000000-0000-0000-0000-000000000001")
OTHER_DOC_ID = UUID("20000000-0000-0000-0000-000000000002")


# ------------------------------------------------------------------
# Fakes
# ------------------------------------------------------------------

class FakeRetriever:
    def __init__(self, chunks):
        self.chunks = chunks

    def __call__(self, state):
        state["retrieved_chunks"] = self.chunks
        return state


class FakeWebSearchTool:
    def execute(self, arguments):
        return {
            "query": arguments["query"],
            "results": [
                {
                    "title": "Java 24 Release Notes",
                    "url": "https://openjdk.org/news/release/jdk24",
                    "snippet": "Java 24 ships with the module import declarations.",
                }
            ],
        }


class FakeSQLTool:
    def execute(self, arguments):
        return {
            "columns": ["count"],
            "rows": [[42]],
            "row_count": 1,
        }


class NoCallLLM:
    """Raises if the responder ever calls the LLM."""

    def generate(self, **kwargs):
        raise AssertionError("deterministic path must not call the LLM")


class RecordingLLM:
    def __init__(self):
        self.user_prompt = None

    def generate(self, *, system_prompt, user_prompt):
        self.user_prompt = user_prompt
        return "synthesis answer"


# ------------------------------------------------------------------
# Specialist success results honor the contract
# ------------------------------------------------------------------

def test_rag_success_result_has_content_and_document_sources():
    chunks = [
        SearchHit(
            chunk_id=UUID("30000000-0000-0000-0000-000000000001"),
            document_id=DOC_ID,
            chunk_index=0,
            content="Employees receive 20 annual leave days.",
            score=0.9,
            document_name="employee_leave_policy.pdf",
        ),
        SearchHit(
            chunk_id=UUID("30000000-0000-0000-0000-000000000002"),
            document_id=DOC_ID,
            chunk_index=1,
            content="Additional days may be negotiated.",
            score=0.8,
            document_name="employee_leave_policy.pdf",
        ),
    ]

    state = {
        "question": "What is our employee leave policy?",
        "user_context": ADMIN,
    }

    result = RAGAgent(FakeRetriever(chunks), breaker=None)(state)

    rag = result["agent_results"]["rag"]
    assert validate_result(rag) == []
    assert rag["success"] is True
    assert "annual leave days" in rag["content"]
    assert rag["sources"] == ["employee_leave_policy.pdf"]
    assert rag["metadata"]["result_count"] == 2


def test_research_success_result_has_content_and_title_url_sources():
    state = {
        "question": "What changed in the latest Java release?",
        "user_context": ADMIN,
    }

    result = ResearchAgent(FakeWebSearchTool(), breaker=None)(state)

    research = result["agent_results"]["research"]
    assert validate_result(research) == []
    assert research["success"] is True
    assert "Java 24" in research["content"]
    assert research["sources"] == [
        "Java 24 Release Notes — https://openjdk.org/news/release/jdk24"
    ]


def test_data_success_result_has_content_source_and_structured_metadata():
    state = {
        "question": "How many orders were completed last month?",
        "user_context": ADMIN,
    }

    result = DataAgent(FakeSQLTool(), breaker=None)(state)

    data = result["agent_results"]["data"]
    assert validate_result(data) == []
    assert data["success"] is True
    assert "Returned 1 row" in data["content"]
    assert data["sources"] == ["database"]
    assert data["metadata"]["rows"] == [[42]]


def test_result_helpers_round_trip():
    raw = {
        "agent": "rag",
        "success": True,
        "content": "x",
        "sources": ["a.pdf"],
        "metadata": {"result_count": 1},
        "error": None,
    }

    assert validate_result(raw) == []

    model = result_to_model(raw)
    assert isinstance(model, AgentResult)
    assert model.sources == ["a.pdf"]


# ------------------------------------------------------------------
# AI policy layer — no fabrication on RAG no-evidence
# ------------------------------------------------------------------

def test_rag_no_evidence_returns_deterministic_answer_without_llm():
    state = {
        "question": "What is the travel reimbursement policy?",
        "agent_results": {
            "rag": {
                "agent": "rag",
                "success": True,
                "content": "",
                "sources": [],
                "metadata": {"result_count": 0},
                "error": None,
            }
        },
    }

    result = ResponderNode(NoCallLLM(), context_builder=None)(state)

    assert result["answer"] == NO_INTERNAL_DOCUMENT_ANSWER
    assert result["citations"] == []


def test_all_failed_permission_denied_is_deterministic_without_llm():
    state = {
        "question": "How many orders were completed?",
        "agent_results": {
            "data": {
                "agent": "data",
                "success": False,
                "content": "",
                "sources": [],
                "metadata": {"permission_denied": True},
                "error": "You are not authorized to execute the data operation.",
            }
        },
    }

    result = ResponderNode(NoCallLLM(), context_builder=None)(state)

    assert result["answer"] == PERMISSION_DENIED_ANSWER


# ------------------------------------------------------------------
# Partial synthesis — only successful evidence, safe failure wording
# ------------------------------------------------------------------

def test_partial_synthesis_uses_only_successful_evidence_and_keeps_sources():
    llm = RecordingLLM()

    state = {
        "question": "Compare our internal architecture with industry practice.",
        "agent_results": {
            "rag": {
                "agent": "rag",
                "success": True,
                "content": "Internal architecture evidence.",
                "sources": ["architecture.adoc"],
                "metadata": {"result_count": 1},
                "error": None,
            },
            "research": {
                "agent": "research",
                "success": False,
                "content": "",
                "sources": [],
                "metadata": {},
                "error": "secret stack trace and credentials",
            },
        },
    }

    result = ResponderNode(llm, context_builder=None)(state)

    assert result["answer"] == "synthesis answer"
    assert result["citations"] == ["architecture.adoc"]
    assert "Internal architecture evidence" in llm.user_prompt
    assert "external research was unavailable" in llm.user_prompt
    assert "secret stack trace" not in llm.user_prompt


def test_collect_sources_deduplicates_across_agents():
    policy = SynthesisPolicy.from_results(
        {
            "rag": {
                "agent": "rag",
                "success": True,
                "content": "a",
                "sources": ["a.pdf", "shared.docx"],
                "metadata": {"result_count": 1},
                "error": None,
            },
            "research": {
                "agent": "research",
                "success": True,
                "content": "b",
                "sources": ["shared.docx", "https://example.com"],
                "metadata": {"result_count": 1},
                "error": None,
            },
        }
    )

    assert policy.collect_sources() == [
        "a.pdf",
        "shared.docx",
        "https://example.com",
    ]