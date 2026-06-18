"""Parse LLM input guard responses."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from llms.input_guard_reviewer.client import call_safety_reviewer
from llms.input_guard_reviewer.prompts import (
    INPUT_GUARD_REVIEWER_SYSTEM_PROMPT,
    build_input_guard_user_message,
)
from workflow.input_guardrails import InputGuardResult, input_guard_decision

_DECISION_RANK = {"pass": 0, "redact": 1, "block": 2}

_ISSUE_TO_RULE: dict[str, str] = {
    "prompt_injection": "llm_prompt_injection",
    "pii_email": "llm_pii_email",
    "pii_phone": "llm_pii_phone",
    "pii_ssn": "llm_pii_ssn",
    "pii_credit_card": "llm_pii_credit_card",
    "out_of_scope_hr_confidential": "llm_out_of_scope_hr_confidential",
    "out_of_scope_medical": "llm_out_of_scope_medical",
    "out_of_scope_legal": "llm_out_of_scope_legal",
    "out_of_scope_general": "llm_out_of_scope_general",
    "out_of_scope_personal": "llm_out_of_scope_personal",
}


@dataclass
class LlmInputGuardReview:
    decision: str
    issues: list[dict[str, str]] = field(default_factory=list)
    sanitized_question: str | None = None
    primary_rule: str | None = None


def _parse_response(response: object) -> LlmInputGuardReview | None:
    if isinstance(response, dict):
        data = response
    elif isinstance(response, str) and response.strip().startswith("{"):
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            return None
    else:
        return None

    decision_raw = data.get("decision")
    if not isinstance(decision_raw, str):
        return None
    decision = decision_raw.strip().lower()
    if decision not in _DECISION_RANK:
        return None

    issues: list[dict[str, str]] = []
    raw_issues = data.get("issues")
    if isinstance(raw_issues, list):
        for item in raw_issues:
            if isinstance(item, dict):
                code = str(item.get("code", "")).strip().lower()
                detail = str(item.get("detail", "")).strip()
                if code and detail:
                    issues.append({"code": code, "detail": detail})

    sanitized = data.get("sanitized_question")
    sanitized_question = (
        str(sanitized).strip() if sanitized is not None and str(sanitized).strip() else None
    )

    primary_rule = None
    if issues:
        primary_rule = _ISSUE_TO_RULE.get(issues[0]["code"], f'llm_{issues[0]["code"]}')

    return LlmInputGuardReview(
        decision=decision,
        issues=issues,
        sanitized_question=sanitized_question,
        primary_rule=primary_rule,
    )


async def run_llm_input_guard_review(
    text: str,
    rule_result: InputGuardResult,
) -> LlmInputGuardReview | None:
    user_content = build_input_guard_user_message(
        user_message=text,
        rule_decision=input_guard_decision(rule_result),
        rule_triggered=rule_result.rule_triggered,
        pii_flags=list(rule_result.pii_detected),
        pii_redacted=rule_result.pii_redacted,
    )
    messages = [
        {"role": "system", "content": INPUT_GUARD_REVIEWER_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    try:
        response = await call_safety_reviewer(messages, temperature=0.0)
    except Exception as exc:
        print(f"  Warning: LLM input guard review unavailable ({exc})")
        return None

    parsed = _parse_response(response)
    if parsed is None:
        print(
            "  Warning: LLM input guard returned unparseable JSON; using rules only."
        )
    return parsed
