import re

from app.prompts.planner import PLANNER_PROMPT
from app.schemas.planner import (
    PlannerAction,
    PlannerDecision,
)


class PlannerNode:
    """
    Decides the NEXT action for the agent.

    PR-21 responsibilities:
    - iterative planning
    - RAG -> planner loop
    - TOOL -> planner loop
    - FINAL
    - retry limit
    - iteration limit
    - tool-call limit
    - destructive-operation protection
    - calculator/SQL routing safety-net
    - SQL -> calculator multi-step flow
    - tool execution history
    """

    MAX_ITERATIONS = 6
    MAX_TOOL_CALLS = 4
    MAX_RETRIES = 2

    def __init__(self, llm):
        self.llm = llm

    def __call__(self, state):

        # ==================================================
        # 1. Initialize loop state
        # ==================================================

        state.setdefault("iteration", 0)
        state.setdefault("tool_call_count", 0)
        state.setdefault("retry_count", 0)
        state.setdefault("tool_executions", [])

        state["iteration"] += 1

        question = state["question"].strip()
        history = state.get("history", [])

        # Clear stale tool request/result only when starting
        # a completely new agent execution.
        if state["iteration"] == 1:
            state["tool_name"] = None
            state["tool_arguments"] = None
            state["tool_result"] = None
            state["tool_error"] = None

        # ==================================================
        # 2. Logging
        # ==================================================

        print("=" * 80)
        print("PLANNER ITERATION:", state["iteration"])
        print("TOOL CALL COUNT:", state["tool_call_count"])
        print("RETRY COUNT:", state["retry_count"])
        print("CURRENT QUESTION:", question)
        print("=" * 80)

        # ==================================================
        # 3. Maximum iteration limit
        # ==================================================

        if state["iteration"] > self.MAX_ITERATIONS:

            state["decision"] = PlannerAction.FINAL.value
            state["decision_reason"] = (
                "planner: maximum iteration limit reached"
            )
            state["tool_name"] = None
            state["tool_arguments"] = None

            self._log_decision(state, question)
            return state

        # ==================================================
        # 4. Retry limit
        #
        # This must happen BEFORE asking the LLM to retry.
        # ==================================================

        if (
            state.get("tool_error")
            and state.get("retry_count", 0)
            >= self.MAX_RETRIES
        ):

            state["decision"] = PlannerAction.FINAL.value
            state["decision_reason"] = (
                "planner: maximum retry limit reached"
            )
            state["tool_name"] = None
            state["tool_arguments"] = None

            self._log_decision(state, question)
            return state

        # ==================================================
        # 5. Tool-call limit
        # ==================================================

        if (
            state.get("tool_call_count", 0)
            >= self.MAX_TOOL_CALLS
        ):

            state["decision"] = PlannerAction.FINAL.value
            state["decision_reason"] = (
                "planner: maximum tool-call limit reached"
            )
            state["tool_name"] = None
            state["tool_arguments"] = None

            self._log_decision(state, question)
            return state

        # ==================================================
        # 6. Build conversation history
        # ==================================================

        previous_user_questions = []

        for message in history[-6:]:
            if message.get("role") == "USER":
                previous_user_questions.append(
                    message.get("content", "")
                
                )
            # else:
            #     if message.role.value == "USER":
            #         previous_user_questions.append(message.content)


        history_text = "\n".join(
            f"USER: {q}"
            for q in previous_user_questions
        )

        # ==================================================
        # 7. Build tool execution history
        # ==================================================

        tool_executions = state.get(
            "tool_executions",
            [],
        )

        if tool_executions:

            tool_history_lines = []

            for index, execution in enumerate(
                tool_executions,
                start=1,
            ):

                tool_history_lines.append(
                    (
                        f"Execution {index}:\n"
                        f"tool={execution.get('tool_name')}\n"
                        f"arguments={execution.get('arguments')}\n"
                        f"success={execution.get('success')}\n"
                        f"result={execution.get('result')}\n"
                        f"error={execution.get('error')}\n"
                        f"iteration={execution.get('iteration')}\n"
                        f"retry_count={execution.get('retry_count')}"
                    )
                )

            tool_history_text = "\n\n".join(
                tool_history_lines
            )

        else:
            tool_history_text = "None"

        # ==================================================
        # 8. Current tool result/error
        # ==================================================

        current_tool_result = state.get(
            "tool_result"
        )

        current_tool_error = state.get(
            "tool_error"
        )

        # ==================================================
        # 9. Retrieved enterprise context
        # ==================================================

        retrieved_chunks = state.get(
            "retrieved_chunks",
            [],
        )

        if retrieved_chunks:

            retrieved_context = "\n\n".join(
                getattr(
                    chunk,
                    "content",
                    str(chunk),
                )
                for chunk in retrieved_chunks
            )

        else:

            retrieved_context = "None"

        # ==================================================
        # 10. Build planner user prompt
        # ==================================================

        prompt_parts = []

        if history_text:

            prompt_parts.append(
                "CONVERSATION HISTORY:\n"
                f"{history_text}"
            )

        prompt_parts.append(
            "CURRENT USER QUESTION:\n"
            f"{question}"
        )

        prompt_parts.append(
            "CURRENT ITERATION:\n"
            f"{state['iteration']}"
        )

        prompt_parts.append(
            "TOOL CALL COUNT:\n"
            f"{state['tool_call_count']}"
        )

        prompt_parts.append(
            "RETRY COUNT:\n"
            f"{state['retry_count']}"
        )

        prompt_parts.append(
            "TOOL EXECUTION HISTORY:\n"
            f"{tool_history_text}"
        )

        prompt_parts.append(
            "CURRENT TOOL RESULT:\n"
            f"{current_tool_result}"
        )

        prompt_parts.append(
            "CURRENT TOOL ERROR:\n"
            f"{current_tool_error}"
        )

        prompt_parts.append(
            "RETRIEVED ENTERPRISE CONTEXT:\n"
            f"{retrieved_context}"
        )

        prompt_parts.append(
            """
Decide the NEXT ACTION.

Rules:

- New enterprise policy/document question -> RAG.
- New calculation -> TOOL / calculator.
- New structured database question -> TOOL / sql.
- Successful RAG result that answers the question -> FINAL.
- Successful tool result that answers the question -> FINAL.
- Successful SQL result that is only an intermediate value -> TOOL.
- Failed tool with retries remaining -> TOOL/retry when useful.
- Failed tool with retry limit reached -> FINAL.
- Unsupported destructive operation -> UNSUPPORTED.
- Essential information missing -> CLARIFY.

Never repeat a successful tool call unnecessarily.
Never choose DIRECT after a successful RAG result that answers the question.
Never choose DIRECT after a successful tool result that answers the question.
"""
        )

        user_prompt = "\n\n".join(prompt_parts)

        print("PLANNER USER PROMPT:")
        print(user_prompt)

        # ==================================================
        # 11. Ask LLM planner
        # ==================================================

        decision = self.llm.generate_structured(
            system_prompt=PLANNER_PROMPT,
            user_prompt=user_prompt,
            schema=PlannerDecision,
        )

        print(
            "LLM Decision object:",
            decision,
        )

        # ==================================================
        # 12. Save raw LLM decision
        # ==================================================

        state["decision"] = decision.action.value

        state["decision_reason"] = (
            decision.reason
            or "llm: no reason provided"
        )

        state["tool_name"] = (
            decision.tool_name
        )

        state["tool_arguments"] = (
            decision.tool_arguments
        )

        # ==================================================
        # 13. Destructive-operation protection
        # ==================================================

        destructive_pattern = re.compile(
            r"\b("
            r"delete|"
            r"remove|"
            r"drop|"
            r"truncate|"
            r"update|"
            r"insert|"
            r"alter|"
            r"destroy|"
            r"rename|"
            r"modify|"
            r"change"
            r")\b",
            re.IGNORECASE,
        )

        if destructive_pattern.search(question):

            state["decision"] = (
                PlannerAction.UNSUPPORTED.value
            )

            state["decision_reason"] = (
                "planner: destructive database "
                "operations are not supported"
            )

            state["tool_name"] = None
            state["tool_arguments"] = None

            self._log_decision(
                state,
                question,
            )

            return state

        # ==================================================
        # 14. Enterprise topic routing safety-net
        #
        # Only force RAG on the first planner iteration.
        # After retrieval, the next iteration can become FINAL.
        # ==================================================

        enterprise_topic = self._looks_like_enterprise_topic(
            question
        )

        if (
            enterprise_topic
            and state["iteration"] == 1
            and decision.action
            not in (
                PlannerAction.UNSUPPORTED,
            )
        ):

            state["decision"] = (
                PlannerAction.RAG.value
            )

            state["decision_reason"] = (
                "planner: explicit enterprise topic -> RAG"
            )

            state["tool_name"] = None
            state["tool_arguments"] = None

            self._log_decision(
                state,
                question,
            )

            return state

        # ==================================================
        # 15. SQL + calculation compound question
        #
        # Example:
        # "How many documents are there multiplied by 10?"
        #
        # First action must be SQL.
        # ==================================================

        if (
            state["iteration"] == 1
            and self._looks_like_sql_calculation(
                question
            )
        ):

            state["decision"] = (
                PlannerAction.TOOL.value
            )

            state["tool_name"] = "sql"

            state["tool_arguments"] = {
                "question": question
            }

            state["decision_reason"] = (
                "planner: SQL result required before "
                "calculator step"
            )

            self._log_decision(
                state,
                question,
            )

            return state

        # ==================================================
        # Existing RAG context already answers the question
        #
        # Once retrieval has produced enterprise context,
        # do not let an unrelated tool failure override it.
        # ==================================================

        if (
            state["iteration"] > 1
            and retrieved_chunks
            and self._looks_like_enterprise_topic(
                question
            )
        ):

            state["decision"] = (
                PlannerAction.FINAL.value
            )

            state["decision_reason"] = (
                "planner: retrieved enterprise context "
                "already answers the question"
            )

            state["tool_name"] = None
            state["tool_arguments"] = None

            self._log_decision(
                state,
                question,
            )

            return state

        # ==================================================
        # 16. Successful previous tool result
        # ==================================================

        if (
            current_tool_result is not None
            and not current_tool_error
        ):

            previous_tool_name = (
                self._last_successful_tool(
                    tool_executions
                )
            )

            # --------------------------------------------------
            # Calculator result
            # --------------------------------------------------

            if previous_tool_name == "calculator":

                # A successful calculator execution is the final
                # step for:
                #
                # 1. Calculate 25 * 40
                #
                # 2. SQL -> calculator
                #
                #    SQL -> 1
                #    Calculator -> 1 * 10 -> 10
                #    FINAL
                #
                # For the compound question:
                #
                # "How many documents are there multiplied by 10?"
                #
                # _looks_like_calculation() is FALSE
                # _looks_like_sql_calculation() is TRUE
                #
                # Therefore we must use OR here.

                if (
                    self._looks_like_calculation(question)
                    or self._looks_like_sql_calculation(question)
                ):

                    state["decision"] = (
                        PlannerAction.FINAL.value
                    )

                    state["decision_reason"] = (
                        "planner: successful calculator result "
                        "already answers the question"
                    )

                    state["tool_name"] = None
                    state["tool_arguments"] = None

                    self._log_decision(
                        state,
                        question,
                    )

                    return state

            # --------------------------------------------------
            # SQL result
            # --------------------------------------------------

            if previous_tool_name == "sql":

                # SQL result is an intermediate value.
                if self._looks_like_sql_calculation(
                    question
                ):

                    calculator_expression = (
                        self._build_calculator_expression_from_sql(
                            question,
                            current_tool_result,
                        )
                    )

                    if calculator_expression:

                        state["decision"] = (
                            PlannerAction.TOOL.value
                        )

                        state["tool_name"] = (
                            "calculator"
                        )

                        state["tool_arguments"] = {
                            "expression":
                                calculator_expression
                        }

                        state["decision_reason"] = (
                            "planner: SQL result is an "
                            "intermediate value for calculator"
                        )

                        self._log_decision(
                            state,
                            question,
                        )

                        return state

                # Ordinary SQL result already answers question.
                state["decision"] = (
                    PlannerAction.FINAL.value
                )

                state["decision_reason"] = (
                    "planner: successful SQL result "
                    "already answers the question"
                )

                state["tool_name"] = None
                state["tool_arguments"] = None

                self._log_decision(
                    state,
                    question,
                )

                return state

            # --------------------------------------------------
            # Web search result
            # --------------------------------------------------
            if previous_tool_name == "web_search":

                state["decision"] = (
                    PlannerAction.FINAL.value
                )

                state["decision_reason"] = (
                    "planner: successful web search result "
                    "is available for the final response"
                )

                state["tool_name"] = None
                state["tool_arguments"] = None

                self._log_decision(
                    state,
                    question,
                )

                return state

            # --------------------------------------------------
            # Support ticket result
            # --------------------------------------------------

            if previous_tool_name == "create_support_ticket":

                state["decision"] = (
                    PlannerAction.FINAL.value
                )

                state["decision_reason"] = (
                    "planner: support ticket was successfully created"
                )

                state["tool_name"] = None
                state["tool_arguments"] = None

                self._log_decision(
                    state,
                    question,
                )

                return state

        # ==================================================
        # Calculator result is already final
        #
        # This is a deterministic safety-net.
        # If calculator already succeeded, never allow
        # the planner to route the same question back to
        # SQL or another tool.
        # ==================================================

        if (
            current_tool_result is not None
            and not current_tool_error
            and previous_tool_name == "calculator"
            and (
                self._looks_like_calculation(question)
                or self._looks_like_sql_calculation(question)
            )
        ):

            state["decision"] = (
                PlannerAction.FINAL.value
            )

            state["decision_reason"] = (
                "planner: calculator result already "
                "completes the requested calculation"
            )

            state["tool_name"] = None
            state["tool_arguments"] = None

            self._log_decision(
                state,
                question,
            )

            return state

        # ==================================================
        # 17. Calculation normalization
        #
        # Prevent LLM from choosing DIRECT for calculations.
        # ==================================================

        if (
            decision.action
            == PlannerAction.DIRECT
            and self._looks_like_calculation(
                question
            )
        ):

            state["decision"] = (
                PlannerAction.TOOL.value
            )

            state["tool_name"] = (
                "calculator"
            )

            state["tool_arguments"] = {
                "expression":
                    self._extract_expression(
                        question
                    )
            }

            state["decision_reason"] = (
                "planner: calculator capability required"
            )

            self._log_decision(
                state,
                question,
            )

            return state

        # ==================================================
        # 18. SQL normalization
        # Prevent LLM from choosing DIRECT/FINAL for
        # structured database questions.
        # ==================================================

        if (
            decision.action
            in (
                PlannerAction.DIRECT,
                PlannerAction.FINAL,
            )
            and self._looks_like_sql(
                question
            )
        ):

            state["decision"] = (
                PlannerAction.TOOL.value
            )

            state["tool_name"] = "sql"

            state["tool_arguments"] = {
                "question": question
            }

            state["decision_reason"] = (
                "planner: SQL capability required"
            )

            self._log_decision(
                state,
                question,
            )

            return state
        
        # support ticket normalization

        
        if (
            state["iteration"] == 1
            and self._looks_like_support_ticket(
                question
            )
        ):

            state["decision"] = (
                PlannerAction.TOOL.value
            )

            state["tool_name"] = (
                "create_support_ticket"
            )

            state["tool_arguments"] = {
                "title": "Support request",
                "description": question,
            }

            state["decision_reason"] = (
                "planner: support ticket capability required"
            )

            self._log_decision(
                state,
                question,
            )

            return state

        # ==================================================
        # 18B. Web search normalization
        # ==================================================
        
        if (
            state["iteration"] == 1
            and decision.action
            in (
                PlannerAction.DIRECT,
                PlannerAction.FINAL,
                PlannerAction.RAG,
            )
            and self._looks_like_web_search(question)            
        ):
        
            state["decision"] = (PlannerAction.TOOL.value)
        
            state["tool_name"] = "web_search"
        
            state["tool_arguments"] = {
                "query": question,
                "max_results": 5,
            }
        
            state["decision_reason"] = (
                "planner: web search capability required"
            )
        
            self._log_decision(
                state,
                question,
            )
        
            return state

        # ==================================================
        # 19. Retrieved context already exists
        # ==================================================

        if (
            state["iteration"] > 1
            and retrieved_chunks
            and not current_tool_error
            and decision.action
            in (
                PlannerAction.DIRECT,
                PlannerAction.RAG,
            )
        ):

            state["decision"] = (
                PlannerAction.FINAL.value
            )

            state["decision_reason"] = (
                "planner: retrieved enterprise "
                "context is sufficient"
            )

            state["tool_name"] = None
            state["tool_arguments"] = None

            self._log_decision(
                state,
                question,
            )

            return state

        # ==================================================
        # 20. Explicit FINAL from LLM
        # ==================================================

        if decision.action == PlannerAction.FINAL:

            # A new calculation must use the calculator tool.
            # Do not allow the LLM to bypass an available
            # application capability by returning FINAL directly.
            if (
                state["iteration"] == 1
                and self._looks_like_calculation(question)
            ):

                state["decision"] = PlannerAction.TOOL.value
                state["tool_name"] = "calculator"
                state["tool_arguments"] = {
                    "expression": self._extract_expression(
                        question
                    )
                }

                state["decision_reason"] = (
                    "planner: calculator capability required"
                )

                self._log_decision(
                    state,
                    question,
                )

                return state

            # A new structured database question must use SQL.
            if (
                state["iteration"] == 1
                and self._looks_like_sql(question)
            ):

                state["decision"] = PlannerAction.TOOL.value
                state["tool_name"] = "sql"
                state["tool_arguments"] = {
                    "question": question
                }

                state["decision_reason"] = (
                    "planner: SQL capability required"
                )

                self._log_decision(
                    state,
                    question,
                )

                return state

            state["tool_name"] = None
            state["tool_arguments"] = None

            self._log_decision(
                state,
                question,
            )

            return state

        # ==================================================
        # 21. TOOL handling
        # ==================================================

        if (
            decision.action
            == PlannerAction.TOOL
        ):

            tool_name = (
                decision.tool_name
            )

            tool_arguments = (
                decision.tool_arguments
            )

            # --------------------------------------------------
            # Recover malformed TOOL metadata
            # --------------------------------------------------

            if (
                not tool_name
                or not isinstance(
                    tool_arguments,
                    dict,
                )
            ):

                # ------------------------------------------
                # Calculator recovery
                # ------------------------------------------

                if self._looks_like_calculation(
                    question
                ):

                    tool_name = (
                        "calculator"
                    )

                    tool_arguments = {
                        "expression":
                            self._extract_expression(
                                question
                            )
                    }

                    state["decision_reason"] = (
                        "planner: recovered malformed TOOL "
                        "decision to calculator"
                    )

                # ------------------------------------------
                # SQL recovery
                # ------------------------------------------

                elif self._looks_like_sql(
                    question
                ):

                    tool_name = "sql"

                    tool_arguments = {
                        "question": question
                    }

                    state["decision_reason"] = (
                        "planner: recovered malformed TOOL "
                        "decision to sql"
                    )

                elif self._looks_like_web_search(question):

                    tool_name = "web_search"

                    tool_arguments = {
                        "query": question,
                        "max_results": 5,
                    }

                    state["decision_reason"] = (
                        "planner: recovered malformed TOOL "
                        "decision to web_search"
                    )

                # ------------------------------------------
                # Unknown malformed TOOL
                # ------------------------------------------

                else:

                    state["decision"] = (
                        PlannerAction.CLARIFY.value
                    )

                    state["decision_reason"] = (
                        "planner: TOOL decision missing "
                        "valid tool metadata"
                    )

                    state["tool_name"] = None
                    state["tool_arguments"] = None

                    self._log_decision(
                        state,
                        question,
                    )

                    return state

            state["tool_name"] = (
                tool_name
            )

            state["tool_arguments"] = (
                tool_arguments
            )

            self._log_decision(
                state,
                question,
            )

            return state

        # ==================================================
        # 22. Explicit UNSUPPORTED
        # ==================================================

        if (
            decision.action
            == PlannerAction.UNSUPPORTED
        ):

            self._log_decision(
                state,
                question,
            )

            return state

        # ==================================================
        # 23. Explicit CLARIFY
        # ==================================================

        if (
            decision.action
            == PlannerAction.CLARIFY
        ):

            self._log_decision(
                state,
                question,
            )

            return state

        # ==================================================
        # 24. Fallback
        # ==================================================

        state["decision"] = (
            PlannerAction.CLARIFY.value
        )

        state["decision_reason"] = (
            "planner: unable to determine a safe next action"
        )

        state["tool_name"] = None
        state["tool_arguments"] = None

        self._log_decision(
            state,
            question,
        )

        return state

    # ======================================================
    # Helpers
    # ======================================================

    @staticmethod
    def _looks_like_calculation(
        question: str,
    ) -> bool:

        return bool(
            re.search(
                r"\bcalculate\b"
                r"|\bcompute\b"
                r"|\d+\s*[\+\-\*/]\s*\d+"
                r"|\bwhat is\s+\d+\s*[\+\-\*/]"
                r"|\bwhat's\s+\d+\s*[\+\-\*/]",
                question,
                re.IGNORECASE,
            )
        )

    @staticmethod
    def _extract_expression(
        question: str,
    ) -> str:

        expression = re.sub(
            r"^\s*"
            r"(calculate|compute|what is|what's)"
            r"\s+",
            "",
            question,
            flags=re.IGNORECASE,
        )

        return (
            expression
            .rstrip(" ?.")
            .strip()
        )

    @staticmethod
    def _looks_like_sql(
        question: str,
    ) -> bool:

        patterns = [
            r"\bhow many\b.*\b(documents|users|records)\b",
            r"\bhow much\b.*\b(documents|users|records)\b",
            r"\bcount\b.*\b(documents|users|records)\b",
            r"\bshow\b.*\b(documents|users|records)\b",
            r"\blist\b.*\b(documents|users|records)\b",
            r"\blatest\b.*\b(documents|users|records)\b",
            r"\bmost recent\b.*\b(documents|users|records)\b",
            r"\brecent\b.*\b(documents|users|records)\b",
            r"\bnumber of\b.*\b(documents|users|records)\b",
            r"\bwhich\b.*\b(documents|users)\b",
        ]

        return any(
            re.search(
                pattern,
                question,
                re.IGNORECASE,
            )
            for pattern in patterns
        )

    @staticmethod
    def _looks_like_sql_calculation(
        question: str,
    ) -> bool:

        return bool(
            re.search(
                r"\b("
                r"how many|"
                r"count|"
                r"number of"
                r")\b"
                r".*"
                r"\b("
                r"multiply|"
                r"multiplied|"
                r"times"
                r")\b"
                r".*\d+",
                question,
                re.IGNORECASE,
            )
        )

    @staticmethod
    def _looks_like_enterprise_topic(
        question: str,
    ) -> bool:

        patterns = (
            r"\bpolic(?:y|ies)\b",
            r"\bleave\b",
            r"\bsick leave\b",
            r"\bannual leave\b",
            r"\breimbursement\b",
            r"\bbenefits?\b",
            r"\bemployee handbook\b",
            r"\bwfh\b",
            r"\bwork from home\b",
            r"\bremote work\b",
            r"\btravel policy\b",
            r"\bcompany procedure\b",
            r"\binternal procedure\b",
        )

        question_lower = question.lower()

        return any(
            re.search(
                pattern,
                question_lower,
                re.IGNORECASE,
            )
            for pattern in patterns
        )

    @staticmethod
    def _looks_like_web_search(
        question: str,
    ) -> bool:

        patterns = [
        r"\blatest\b",
        r"\brecent\b",
        r"\bcurrently\b",
        r"\bcurrent\b",
        r"\btoday\b",
        r"\byesterday\b",
        r"\bthis week\b",
        r"\bthis month\b",
        r"\bthis year\b",
        r"\bnews\b",
        r"\bdevelopments?\b",
        r"\bwhat happened\b",
        r"\bnew release\b",
        r"\blatest release\b",
        r"\bnew version\b",
        r"\blatest version\b",
        r"\bcurrent version\b",
        r"\bannouncements?\b",
        r"\bpublic web\b",
        r"\bonline\b",
    ]

        question_lower = question.lower()

        return any(
            re.search(
                pattern,
                question_lower,
                re.IGNORECASE,
            )
            for pattern in patterns
        )

    @staticmethod
    def _looks_like_support_ticket(
        question: str,
    ) -> bool:

        patterns = [
            r"\bcreate\b.*\bsupport ticket\b",
            r"\bcreate\b.*\bticket\b",
            r"\braise\b.*\bticket\b",
            r"\bopen\b.*\bticket\b",
            r"\bcreate\b.*\bsupport case\b",
        ]

        return any(
            re.search(
                pattern,
                question,
                re.IGNORECASE,
            )
            for pattern in patterns
        )

    @staticmethod
    def _last_successful_tool(
        tool_executions,
    ) -> str | None:

        for execution in reversed(
            tool_executions
        ):

            if execution.get("success"):

                return execution.get(
                    "tool_name"
                )

        return None

    @staticmethod
    def _build_calculator_expression_from_sql(
        question: str,
        result,
    ) -> str | None:

        if not isinstance(result, dict):
            return None

        rows = result.get("rows") or []

        if not rows:
            return None

        first_row = rows[0]

        if not first_row:
            return None

        value = first_row[0]

        multiplier_match = re.search(
            r"\b(?:multiply|multiplied|times)"
            r"\s+(?:by\s+)?"
            r"(\d+(?:\.\d+)?)",
            question,
            re.IGNORECASE,
        )

        if not multiplier_match:
            return None

        multiplier = (
            multiplier_match.group(1)
        )

        return (
            f"{value} * {multiplier}"
        )

    @staticmethod
    def _log_decision(
        state,
        question,
    ):

        print("=" * 80)
        print(
            "FINAL PLANNER DECISION:",
            state.get("decision"),
        )
        print(
            "QUESTION:",
            question,
        )
        print(
            "REASON:",
            state.get("decision_reason"),
        )
        print(
            "ITERATION:",
            state.get("iteration"),
        )
        print(
            "TOOL CALL COUNT:",
            state.get("tool_call_count"),
        )
        print(
            "RETRY COUNT:",
            state.get("retry_count"),
        )
        print(
            "TOOL:",
            state.get("tool_name"),
        )
        print(
            "TOOL ARGUMENTS:",
            state.get("tool_arguments"),
        )
        print("=" * 80)