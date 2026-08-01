import json

from app.prompts.planner import PLANNER_PROMPT
from app.schemas.planner import PlannerDecision


class PlannerNode:

    def __init__(self, llm):

        self.llm = llm

    def __call__(self, state):

        response = self.llm.generate(

            system_prompt=PLANNER_PROMPT,

            user_prompt=state["question"],
        )

        decision = PlannerDecision.model_validate_json(response)

        state["decision"] = decision.action.value

        return state