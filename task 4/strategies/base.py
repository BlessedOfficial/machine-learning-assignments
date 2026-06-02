from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Problem:
    id: str
    question: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceStep:
    step_type: str  # e.g. "thought", "action", "observation", "plan", "execute"
    content: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Trace:
    strategy: str
    problem_id: str
    steps: list[TraceStep] = field(default_factory=list)
    answer: str = ""


class Strategy(Protocol):
    name: str

    async def solve(self, problem: Problem) -> Trace: ...
