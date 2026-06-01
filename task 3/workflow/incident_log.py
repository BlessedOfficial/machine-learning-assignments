"""Structured incident logging for guardrail rejections."""

import json
from datetime import datetime, timezone
from pathlib import Path

from config import GUARDRAIL_INCIDENT_LOG_PATH, LOG_GUARDRAIL_INCIDENTS
from workflow.pii_utils import redact_pii


def redact_for_log(text: str) -> str:
    redacted, _ = redact_pii(text or "", allow_corporate_email=True)
    return redacted


def log_guardrail_incident(
    *,
    rule_triggered: str,
    raw_input: str,
    decision: str = "block",
    stage: str = "input",
    detail: str | None = None,
) -> None:
    """
    Append a structured incident entry for every guardrail rejection.

    Fields: timestamp, rule_triggered, redacted_input, decision.
    """
    if not LOG_GUARDRAIL_INCIDENTS or not GUARDRAIL_INCIDENT_LOG_PATH:
        return

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rule_triggered": rule_triggered,
        "redacted_input": redact_for_log(raw_input),
        "decision": decision,
        "stage": stage,
    }
    if detail:
        payload["detail"] = detail

    log_path = Path(GUARDRAIL_INCIDENT_LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")
