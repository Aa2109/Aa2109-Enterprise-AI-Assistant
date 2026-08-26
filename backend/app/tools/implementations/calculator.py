import ast
import operator as op

from app.tools.base import BaseTool
from app.tools.schemas import CalculatorInput


class CalculatorTool(BaseTool):

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return (
            "Perform basic mathematical calculations. "
            "Supports addition, subtraction, multiplication, "
            "division, and parentheses."
        )

    def execute(self, arguments: dict) -> float:
        validated = CalculatorInput.model_validate(arguments)

        return self._evaluate(validated.expression)

    def _evaluate(self, expression: str) -> float:
        node = ast.parse(expression, mode="eval").body

        return self._eval_node(node)

    def _eval_node(self, node):
        operators = {
            ast.Add: op.add,
            ast.Sub: op.sub,
            ast.Mult: op.mul,
            ast.Div: op.truediv,
        }

        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value

            raise ValueError("Only numeric values are allowed.")

        if isinstance(node, ast.BinOp):
            operator = operators.get(type(node.op))

            if operator is None:
                raise ValueError("Unsupported mathematical operator.")

            left = self._eval_node(node.left)
            right = self._eval_node(node.right)

            return operator(left, right)

        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return -self._eval_node(node.operand)

            if isinstance(node.op, ast.UAdd):
                return self._eval_node(node.operand)

        if isinstance(node, ast.Expression):
            return self._eval_node(node.body)

        raise ValueError("Invalid mathematical expression.")