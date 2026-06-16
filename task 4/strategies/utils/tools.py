"""Calculator and Python executor shared by reasoning strategies."""

import ast
import operator
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from Observability.context import get_trace_context
from strategies.utils.config import CODE_EXEC_TIMEOUT

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


def _log_tool_call(
    tool: str,
    inputs: dict,
    outputs: dict,
    latency_ms: float,
    *,
    error: str | None = None,
) -> None:
    ctx = get_trace_context()
    if ctx is None:
        return
    metadata = {"error": error} if error else {}
    ctx.logger.log_tool_call(
        trace_id=ctx.trace_id,
        strategy=ctx.strategy,
        problem_id=ctx.problem_id,
        tool=tool,
        inputs=inputs,
        outputs=outputs,
        latency_ms=latency_ms,
        metadata=metadata,
    )


def calculate(expression: str) -> str:
    """Evaluate a numeric expression for ReAct / Plan-and-Execute."""
    started = time.perf_counter()
    expr = expression.strip().replace(",", "").replace("$", "").replace("%", "/100")
    try:
        if not expr:
            raise ValueError("Empty expression")
        if not re.fullmatch(r"[\d\s+\-*/().%]+", expr.replace("/100", "")):
            raise ValueError("Expression contains unsupported characters")

        tree = ast.parse(expr, mode="eval")
        value = _eval_node(tree.body)
        if float(value).is_integer():
            result = str(int(value))
        else:
            result = str(value)
        _log_tool_call(
            "calculator",
            {"expression": expression},
            {"result": result},
            (time.perf_counter() - started) * 1000,
        )
        return result
    except Exception as exc:
        _log_tool_call(
            "calculator",
            {"expression": expression},
            {},
            (time.perf_counter() - started) * 1000,
            error=str(exc),
        )
        raise


def extract_python_code(raw: str) -> str:
    text = raw.strip()
    fence = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    return text


def run_python_code(code: str, *, timeout: float | None = None) -> str:
    """Run generated Python in a subprocess with strict timeout (PoT sandbox)."""
    started = time.perf_counter()
    cleaned = extract_python_code(code)
    exec_timeout = CODE_EXEC_TIMEOUT if timeout is None else timeout
    try:
        if not cleaned:
            raise ValueError("No Python code to execute")

        fd, name = tempfile.mkstemp(suffix=".py")
        os.close(fd)
        path = Path(name)
        try:
            path.write_text(cleaned, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(path)],
                capture_output=True,
                text=True,
                timeout=exec_timeout,
            )
            if result.returncode != 0:
                err = (result.stderr or result.stdout or "execution failed").strip()
                raise RuntimeError(err)
            stdout = result.stdout.strip()
            _log_tool_call(
                "python",
                {"code": cleaned, "timeout_sec": exec_timeout},
                {"stdout": stdout},
                (time.perf_counter() - started) * 1000,
            )
            return stdout
        finally:
            path.unlink(missing_ok=True)
    except Exception as exc:
        _log_tool_call(
            "python",
            {"code": cleaned, "timeout_sec": exec_timeout},
            {},
            (time.perf_counter() - started) * 1000,
            error=str(exc),
        )
        raise
