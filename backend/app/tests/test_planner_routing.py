import pytest

from app.agents.nodes.planner import PlannerNode
from app.schemas.planner import PlannerDecision, PlannerAction


class DummyLLM:
    def __init__(self, decision_obj):
        self._decision = decision_obj

    def generate_structured(self, system_prompt, user_prompt, schema):
        return self._decision


def test_policy_question_forces_rag_over_direct():
    # LLM returns DIRECT but question is enterprise policy -> heuristic should force RAG
    llm = DummyLLM(PlannerDecision(action=PlannerAction.DIRECT, reason="llm: guessed direct"))
    node = PlannerNode(llm)
    state = {"question": "How many sick leave days do employees get?", "history": []}

    out = node(state)
    assert out["decision"] == "RAG"
    assert "policy" in out.get("decision_reason", "") or "heuristic" in out.get("decision_reason", "")


def test_capital_question_forces_direct_over_clarify():
    # LLM returns CLARIFY but question is simple world-fact -> heuristic should force DIRECT
    llm = DummyLLM(PlannerDecision(action=PlannerAction.CLARIFY, reason="llm: asked to clarify"))
    node = PlannerNode(llm)
    state = {"question": "What is the capital of France?", "history": []}

    out = node(state)
    assert out["decision"] == "DIRECT"
    assert "general world-fact" in out.get("decision_reason", "") or "heuristic" in out.get("decision_reason", "")


def test_math_question_forces_direct():
    # LLM returns CLARIFY but simple math should be DIRECT
    llm = DummyLLM(PlannerDecision(action=PlannerAction.CLARIFY, reason="llm: unclear"))
    node = PlannerNode(llm)
    state = {"question": "What is 25 * 4?", "history": []}

    out = node(state)
    assert out["decision"] == "DIRECT"
    assert "math" in out.get("decision_reason", "") or "heuristic" in out.get("decision_reason", "")


def test_leave_policy_question_routes_to_rag():
    llm = DummyLLM(PlannerDecision(action=PlannerAction.DIRECT, reason="llm: guessed direct"))
    node = PlannerNode(llm)
    state = {"question": "What is the leave policy?", "history": []}

    out = node(state)
    assert out["decision"] == "RAG"
    assert "policy" in out.get("decision_reason", "") or "heuristic" in out.get("decision_reason", "")


def test_destructive_sql_request_is_blocked():
    llm = DummyLLM(PlannerDecision(action=PlannerAction.TOOL, reason="llm: selected tool", tool_name="sql", tool_arguments={"question": "Delete all documents."}))
    node = PlannerNode(llm)
    state = {"question": "Delete all documents.", "history": []}

    out = node(state)
    assert out["decision"] == "DIRECT"
    assert out.get("tool_name") is None
    assert out.get("tool_arguments") is None
