"""Backward-compatible re-exports."""

from llms.base import LLMResult, call_llm
from llms.judge import judge_answer
from llms.solver import ask, ask_with_metadata

__all__ = [
    "LLMResult",
    "ask",
    "ask_with_metadata",
    "call_llm",
    "judge_answer",
]
