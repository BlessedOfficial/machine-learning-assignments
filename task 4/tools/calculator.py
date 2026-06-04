"""Safe arithmetic for ReAct calculator tool (shared across strategies)."""

import ast
import operator
import re

_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARYOPS:
        return _UNARYOPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        return _BINOPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    raise ValueError("Unsupported expression")


def calculate(expression: str) -> str:
    """
    Evaluate a numeric expression. Supports + - * / // % ** and parentheses.
    Returns result as string (int if whole number).
    """
    expr = expression.strip().replace(",", "").replace("$", "").replace("%", "/100")
    if not expr:
        raise ValueError("Empty expression")
    if not re.fullmatch(r"[\d\s+\-*/().%]+", expr.replace("/100", "")):
        raise ValueError("Expression contains unsupported characters")

    tree = ast.parse(expr, mode="eval")
    value = _eval_node(tree.body)
    if float(value).is_integer():
        return str(int(value))
    return str(value)
