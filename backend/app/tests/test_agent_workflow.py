"""PR-30 — end-to-end workflow tests through the compiled LangGraph.

Each test drives the real ``build_graph()`` with stub memory nodes and
scripted supervisor / responder LLMs, proving the full supervisor loop

    memory → supervisor → specialist(s) → supervisor → responder

for the core PR-30 scenarios:

- Scenario A — RAG-only internal knowledge
- Scenario B — research-only external knowledge
- Scenario D — multi-agent (RAG + Research) → synthesis + citations
- Failure-aware degradation — a failed agent yields a partial answer
- RBAC denial — an unauthorized specialist yields the deterministic
  "not authorized" answer without any LLM call
"""

from uuid import UUID, uuid4

from app.agents.graph import build_graph
from app.agents.nodes.responder import ResponderNode
from app.agents.specialists.data_agent import DataAgent
from app.agents.specialists.rag_agent import RAGAgent
from app.agents.specialists.research_agent import ResearchAgent
from app.agents.supervisor import Supervisor
from app.agents.synthesis import PERMISSION_DENIED_ANSWER
from app.schemas.agents_schema import AgentName, RoutingDecision
from app.schemas.search import SearchHit
from app.security.models import Role, UserContext
from app.security.rbac import permissions_for_role

DOC_ID = UUID("10000000-0000-0000-0000-000000000001")


def make_user(role: Role) -> UserContext:
    return UserContext(
        user_id="00000000-0000-0000-0000-00000000000a",
        role=role,
        permissions=permissions_for_role(role),
    )


def default_state(**overrides) -> dict:
    """Mirror the state RAGService constructs, minus DB dependencies."""
    state = {
        "question": "What is our employee leave policy?",
        "owner_id": UUID("00000000-0000-0000-0000-00000000000a"),
        "history": [],
        "user_context": make_user(Role.ADMIN),
        "run_id": str(uuid4()),
        "selected_agents": [],
        "pending_agents": [],
        "current_agent": None,
        "supervisor_reason": None,
        "done": False,
        "supervisor_done": False,
        "agent_step": 0,
        "agent_results": {},
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "token_budget_exceeded": False,
        "answer": None,
        "citations": [],
    }
    state.update(overrides)
    return state


def graph_config() -> dict:
    return {"configurable": {"thread_id": str(uuid4())}}


# ------------------------------------------------------------------
# Stubs / fakes
# ------------------------------------------------------------------

def stub_memory_retriever(state):
    state["retrieved_memories"] = []
    return state


def stub_memory_extractor(state):
    return state


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


class FailingWebSearchTool:
    def execute(self, arguments):
        raise RuntimeError("search service unavailable")


class FakeSQLTool:
    def execute(self, arguments):
        return {
            "columns": ["count"],
            "rows": [[42]],
            "row_count": 1,
        }


class ScriptedSupervisorLLM:
    """Returns a scripted RoutingDecision per call, in order.

    The last decision is reused for any further call, so tests only
    script the decisions they expect.
    """

    def __init__(self, *decisions: RoutingDecision):
        self.decisions = list(decisions)
        self.calls = 0

    def generate_structured(self, **kwargs):
        decision = self.decisions[
            min(self.calls, len(self.decisions) - 1)
        ]
        self.calls += 1
        return decision


class RecordingLLM:
    def __init__(self):
        self.user_prompt = None

    def generate(self, *, system_prompt, user_prompt):
        self.user_prompt = user_prompt
        return "synthesis answer"


class NoCallLLM:
    def generate(self, **kwargs):
        raise AssertionError("deterministic path must not call the LLM")


RAG_CHUNKS = [
    SearchHit(
        chunk_id=UUID("30000000-0000-0000-0000-000000000001"),
        document_id=DOC_ID,
        chunk_index=0,
        content="Internal architecture evidence: supervisor agents.",
        score=0.9,
        document_name="architecture.adoc",
    ),
    SearchHit(
        chunk_id=UUID("30000000-0000-0000-0000-000000000002"),
        document_id=DOC_ID,
        chunk_index=1,
        content="Employees receive 20 annual leave days.",
        score=0.85,
        document_name="employee_leave_policy.pdf",
    ),
]


def build_test_graph(scripted_decisions, responder_llm):
    """Wire the real graph with stub memory nodes and scripted LLMs."""
    return build_graph(
        responder=ResponderNode(
            responder_llm, context_builder=None
        ),
        memory_retriever_node=stub_memory_retriever,
        memory_extractor_node=stub_memory_extractor,
        supervisor=Supervisor(
            ScriptedSupervisorLLM(*scripted_decisions)
        ),
        rag_agent=RAGAgent(FakeRetriever(RAG_CHUNKS), breaker=None),
        research_agent=ResearchAgent(
            FakeWebSearchTool(), breaker=None
        ),
        data_agent=DataAgent(FakeSQLTool(), breaker=None),
    )


# ------------------------------------------------------------------
# Scenario A — RAG-only
# ------------------------------------------------------------------

def test_scenario_a_rag_only_end_to_end():
    llm = RecordingLLM()

    graph = build_test_graph(
        [
            RoutingDecision(
                agents=[AgentName.RAG],
                reasoning="internal knowledge",
                done=False,
            ),
            RoutingDecision(
                agents=[],
                reasoning="enough evidence",
                done=True,
            ),
        ],
        llm,
    )

    result = graph.invoke(
        default_state(),
        config=graph_config(),
    )

    assert result["answer"] == "synthesis answer"
    # RAG document names surface as citations, no research sources.
    assert set(result["citations"]) == {
        "architecture.adoc",
        "employee_leave_policy.pdf",
    }
    # The responder saw the successful RAG evidence.
    assert "Internal architecture evidence" in llm.user_prompt
    assert "https://openjdk.org" not in (llm.user_prompt or "")


# ------------------------------------------------------------------
# Scenario B — research-only
# ------------------------------------------------------------------

def test_scenario_b_research_only_end_to_end():
    llm = RecordingLLM()

    graph = build_test_graph(
        [
            RoutingDecision(
                agents=[AgentName.RESEARCH],
                reasoning="external knowledge",
                done=False,
            ),
            RoutingDecision(
                agents=[],
                reasoning="enough evidence",
                done=True,
            ),
        ],
        llm,
    )

    result = graph.invoke(
        default_state(question="What changed in the latest Java release?"),
        config=graph_config(),
    )

    assert result["answer"] == "synthesis answer"
    assert result["citations"] == [
        "Java 24 Release Notes — https://openjdk.org/news/release/jdk24"
    ]
    assert "Java 24" in llm.user_prompt


# ------------------------------------------------------------------
# Scenario D — multi-agent: RAG + Research, then synthesis
# ------------------------------------------------------------------

def test_scenario_d_multi_agent_synthesis():
    llm = RecordingLLM()

    graph = build_test_graph(
        [
            # Pathological router turn: done=true WITH a non-empty agent
            # list, before any specialist has run. The routing bug —
            # checking done() before pending specialists — would send
            # this straight to the responder with zero evidence (an
            # empty, hallucination-prone synthesis). Pending specialists
            # must always win.
            RoutingDecision(
                agents=[AgentName.RAG, AgentName.RESEARCH],
                reasoning="compare internal with industry",
                done=True,
            ),
            RoutingDecision(
                agents=[],
                reasoning="done",
                done=True,
            ),
        ],
        llm,
    )

    result = graph.invoke(
        default_state(
            question="Compare our internal architecture with industry practice."
        ),
        config=graph_config(),
    )

    # Both agents ran: the responder synthesized from BOTH sources.
    assert result["answer"] == "synthesis answer"
    assert set(result["citations"]) == {
        "architecture.adoc",
        "employee_leave_policy.pdf",
        "Java 24 Release Notes — https://openjdk.org/news/release/jdk24",
    }
    assert "supervisor agents" in llm.user_prompt
    assert "Java 24" in llm.user_prompt


# ------------------------------------------------------------------
# Scenario C — data-only
# ------------------------------------------------------------------

def test_scenario_c_data_only_end_to_end():
    llm = RecordingLLM()

    graph = build_test_graph(
        [
            RoutingDecision(
                agents=[AgentName.DATA],
                reasoning="structured data",
                done=False,
            ),
            RoutingDecision(
                agents=[],
                reasoning="enough evidence",
                done=True,
            ),
        ],
        llm,
    )

    result = graph.invoke(
        default_state(
            question="How many orders were completed last month?",
            user_context=make_user(Role.ANALYST),  # has DATA_READ
        ),
        config=graph_config(),
    )

    assert result["answer"] == "synthesis answer"
    assert result["citations"] == ["database"]
    assert "Returned 1 row" in llm.user_prompt
    assert "42" in llm.user_prompt  # the structured value reached the responder


# ------------------------------------------------------------------
# Failure-aware degradation — research fails, RAG succeeds
# ------------------------------------------------------------------

def test_partial_synthesis_on_agent_failure():
    llm = RecordingLLM()

    graph = build_graph(
        responder=ResponderNode(llm, context_builder=None),
        memory_retriever_node=stub_memory_retriever,
        memory_extractor_node=stub_memory_extractor,
        supervisor=Supervisor(
            ScriptedSupervisorLLM(
                RoutingDecision(
                    agents=[AgentName.RAG, AgentName.RESEARCH],
                    reasoning="needs both",
                    done=False,
                ),
                RoutingDecision(
                    agents=[],
                    reasoning="enough",
                    done=True,
                ),
            )
        ),
        rag_agent=RAGAgent(FakeRetriever(RAG_CHUNKS), breaker=None),
        research_agent=ResearchAgent(
            FailingWebSearchTool(), breaker=None
        ),
        data_agent=DataAgent(FakeSQLTool(), breaker=None),
    )

    result = graph.invoke(
        default_state(question="Compare internal vs industry practice."),
        config=graph_config(),
    )

    # A partial answer survives the failed research agent — no 500.
    assert result["answer"] == "synthesis answer"
    # RAG evidence is used; the research failure is reported honestly
    # with safe wording, never a raw exception.
    assert "Internal architecture evidence" in llm.user_prompt
    assert "external research was unavailable" in llm.user_prompt
    assert "search service unavailable" not in (llm.user_prompt or "")
    # Research produced no citations.
    assert "openjdk.org" not in result["citations"]


# ------------------------------------------------------------------
# RBAC denial — deterministic answer, no LLM
# ------------------------------------------------------------------

def test_rbac_denial_is_deterministic_end_to_end():
    graph = build_test_graph(
        [
            RoutingDecision(
                agents=[AgentName.DATA],
                reasoning="structured data",
                done=False,
            ),
        ],
        NoCallLLM(),
    )

    result = graph.invoke(
        default_state(
            question="How many orders were completed last month?",
            user_context=make_user(Role.USER),  # no DATA_READ
        ),
        config=graph_config(),
    )

    assert result["answer"] == PERMISSION_DENIED_ANSWER
    assert result["citations"] == []
    # The denial is recorded as a structured, non-retryable failure so
    # the supervisor never attempts the data specialist again.
    denied = result["agent_results"]["data"]
    assert denied["success"] is False
    assert denied["metadata"]["permission_denied"] is True


# ------------------------------------------------------------------
# Memory — same-conversation follow-up reaches the final responder
# ------------------------------------------------------------------

def test_memory_followup_injected_into_final_answer():
    """A follow-up must see stored + retrieved user memory.

    Regression for the §14 matrix row: after "My name is Aashif." the
    in-conversation follow-up "What is my name?" returned "Unknown".
    The memory was saved and retrieved (PostgreSQL + Qdrant) but the
    responder's FINAL branch built the prompt from the question alone.
    The final response must now include both the retrieved memory and
    the bounded recent conversation history.
    """
    llm = RecordingLLM()

    owner_id = UUID("00000000-0000-0000-0000-00000000000a")

    class MemoryStub:
        def __call__(self, state):
            state["retrieved_memories"] = [
                {
                    "memory_id": str(uuid4()),
                    "user_id": str(owner_id),
                    "content": "The user's name is Aashif.",
                    "memory_type": "semantic",
                    "importance": 0.5,
                    "score": 0.67,
                }
            ]
            return state

    graph = build_graph(
        responder=ResponderNode(llm, context_builder=None),
        memory_retriever_node=MemoryStub(),
        memory_extractor_node=stub_memory_extractor,
        supervisor=Supervisor(
            ScriptedSupervisorLLM(
                RoutingDecision(
                    agents=[],
                    reasoning="no specialist needed",
                    done=True,
                )
            )
        ),
        rag_agent=RAGAgent(FakeRetriever(RAG_CHUNKS), breaker=None),
        research_agent=ResearchAgent(
            FakeWebSearchTool(), breaker=None
        ),
        data_agent=DataAgent(FakeSQLTool(), breaker=None),
    )

    result = graph.invoke(
        default_state(
            owner_id=owner_id,
            question="What is my name? Reply in one word.",
            history=[
                {"role": "user", "content": "My name is Aashif."},
                {"role": "assistant", "content": "Nice to meet you, Aashif!"},
            ],
        ),
        config=graph_config(),
    )

    assert result["answer"] == "synthesis answer"
    assert result["citations"] == []
    # Both the retrieved memory and the previous turn must reach the LLM.
    assert llm.user_prompt is not None
    assert "The user's name is Aashif." in llm.user_prompt
    assert "My name is Aashif." in llm.user_prompt