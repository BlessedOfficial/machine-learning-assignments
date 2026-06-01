"""Q&A entry point — delegates to the multi-agent orchestrator."""

from pathlib import Path

from agents.orchestrator_agent import OrchestratorAgent
from agents.pipeline_log import PipelineRunLog
from agents.protocol import UserRequest
from agents.trace import RequestTrace
from config import PIPELINE_LOG_DIR


async def answer_question(
    question: str,
    *,
    top_k: int | None = None,
    min_score: float | None = None,
    user_role: str | None = None,
    trace: bool = False,
    run_label: str = "live",
) -> str | tuple[str, RequestTrace, Path | None, PipelineRunLog]:
    orchestrator = OrchestratorAgent()
    request = UserRequest(
        question=question,
        user_role=user_role,
        top_k=top_k,
        min_score=min_score,
    )
    answer, request_trace, trace_path, pipeline_log = await orchestrator.run(
        request, run_label=run_label
    )
    pipeline_log.save(Path(PIPELINE_LOG_DIR))
    if trace:
        return answer, request_trace, trace_path, pipeline_log
    return answer
