"""Live incremental console logging for pipeline steps."""

from __future__ import annotations

from config import SHOW_PIPELINE_LOG

_SEPARATOR = "-" * 72


class PipelineConsole:
    """Prints agent-named steps as the pipeline runs."""

    def __init__(self, *, enabled: bool | None = None) -> None:
        self.enabled = SHOW_PIPELINE_LOG if enabled is None else enabled
        self._steps: list[dict[str, str]] = []

    def header(self, agent: str, title: str) -> None:
        if not self.enabled:
            return
        print(_SEPARATOR, flush=True)
        print(f"[{agent}]  {title}", flush=True)

    def step(
        self,
        agent: str,
        step_name: str,
        *,
        result: str,
        detail: str | None = None,
    ) -> None:
        self._steps.append(
            {"agent": agent, "step": step_name, "result": result, "detail": detail or ""}
        )
        if not self.enabled:
            return
        print(f"  Step     : {step_name}", flush=True)
        print(f"  Result   : {result}", flush=True)
        if detail:
            print(f"  Detail   : {detail}", flush=True)

    def blank(self) -> None:
        if self.enabled:
            print(flush=True)

    def format_recap(self, *, question: str, final_answer: str | None) -> str:
        lines = [
            "",
            "=" * 72,
            "PIPELINE RECAP",
            "=" * 72,
            f"Question: {question}",
            f"Steps logged: {len(self._steps)}",
            "",
            "--- FINAL ANSWER ---",
            final_answer or "(none)",
            "",
            "=" * 72,
        ]
        return "\n".join(lines)

    def print_recap(self, *, question: str, final_answer: str | None) -> None:
        if self.enabled:
            print(self.format_recap(question=question, final_answer=final_answer), flush=True)


# Module-level console for agents that lack orchestrator reference.
_active_console: PipelineConsole | None = None


def get_pipeline_console() -> PipelineConsole:
    global _active_console
    if _active_console is None:
        _active_console = PipelineConsole()
    return _active_console


def set_pipeline_console(console: PipelineConsole | None) -> None:
    global _active_console
    _active_console = console
