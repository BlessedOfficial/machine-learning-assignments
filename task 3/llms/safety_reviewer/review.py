"""Parse LLM safety reviewer responses into pipeline verdicts."""

from __future__ import annotations

from dataclasses import dataclass, field

from agents.protocol import ReviewDecision, SafetyIssue, SafetyIssueCode
from llms.safety_reviewer.client import call_safety_reviewer
from llms.safety_reviewer.prompts import (
    SAFETY_REVIEWER_SYSTEM_PROMPT,
    build_safety_review_user_message,
)
from workflow.prompts import OUT_OF_SCOPE_REPLY

_LLM_CODE_MAP: dict[str, SafetyIssueCode] = {
    "response_meta_leak": SafetyIssueCode.RESPONSE_META_LEAK,
    "citation_discipline": SafetyIssueCode.CITATION_DISCIPLINE,
    "grounding_failure": SafetyIssueCode.GROUNDING_FAILURE,
    "pii_email": SafetyIssueCode.PII_EMAIL,
    "pii_phone": SafetyIssueCode.PII_PHONE,
    "pii_ssn": SafetyIssueCode.PII_SSN,
    "pii_credit_card": SafetyIssueCode.PII_CREDIT_CARD,
    "out_of_scope": SafetyIssueCode.GROUNDING_FAILURE,
    "unsupported_claim": SafetyIssueCode.GROUNDING_FAILURE,
}

_DECISION_RANK = {
    ReviewDecision.APPROVE: 0,
    ReviewDecision.REDACT: 1,
    ReviewDecision.REGENERATE: 2,
}


@dataclass
class LlmSafetyReview:
    decision: ReviewDecision
    issues: list[SafetyIssue] = field(default_factory=list)
    safe_answer: str | None = None
    blocked: bool = False


def _to_text(response: object) -> str:
    if isinstance(response, str):
        return response.strip()
    if isinstance(response, dict):
        for key in ("safe_answer", "answer", "content", "response", "text"):
            if key in response and response[key]:
                return str(response[key]).strip()
        return str(response)
    return str(response).strip() if response is not None else ""


def _parse_decision(raw: object) -> tuple[ReviewDecision | None, bool]:
    if not isinstance(raw, str):
        return None, False
    normalized = raw.strip().lower()
    if normalized == "block":
        return ReviewDecision.APPROVE, True
    for decision in ReviewDecision:
        if decision.value == normalized:
            return decision, False
    return None, False


def _parse_issues(raw: object) -> list[SafetyIssue]:
    if not isinstance(raw, list):
        return []
    issues: list[SafetyIssue] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        code_raw = str(item.get("code", "")).strip().lower()
        detail = str(item.get("detail", "")).strip()
        if not detail:
            continue
        code = _LLM_CODE_MAP.get(code_raw, SafetyIssueCode.GROUNDING_FAILURE)
        issues.append(SafetyIssue(code=code, detail=detail))
    return issues


def parse_llm_safety_response(response: object) -> LlmSafetyReview | None:
    if isinstance(response, dict):
        data = response
    elif isinstance(response, str) and response.strip().startswith("{"):
        import json

        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            return None
    else:
        return None

    decision, blocked = _parse_decision(data.get("decision"))
    if decision is None:
        return None

    safe_answer_raw = data.get("safe_answer")
    safe_answer = (
        str(safe_answer_raw).strip() if safe_answer_raw is not None else None
    )
    if safe_answer == "":
        safe_answer = None
    if blocked:
        safe_answer = safe_answer or block_verdict_safe_answer()

    return LlmSafetyReview(
        decision=decision,
        issues=_parse_issues(data.get("issues")),
        safe_answer=safe_answer,
        blocked=blocked,
    )


def merge_decisions(
    rule_decision: ReviewDecision, llm_decision: ReviewDecision
) -> ReviewDecision:
    if _DECISION_RANK[llm_decision] > _DECISION_RANK[rule_decision]:
        return llm_decision
    return rule_decision


def merge_critiques(
    rule_critique: list[SafetyIssue], llm_critique: list[SafetyIssue]
) -> list[SafetyIssue]:
    seen: set[tuple[str, str]] = set()
    merged: list[SafetyIssue] = []
    for issue in rule_critique + llm_critique:
        key = (issue.code.value, issue.detail)
        if key in seen:
            continue
        seen.add(key)
        merged.append(issue)
    return merged


def block_verdict_safe_answer() -> str:
    return OUT_OF_SCOPE_REPLY


async def run_llm_safety_review(
    *,
    question: str,
    draft: str,
    hits: list[dict],
    rule_decision: ReviewDecision,
    rule_critique: list[SafetyIssue],
    processed_answer: str,
) -> LlmSafetyReview | None:
    user_content = build_safety_review_user_message(
        question=question,
        draft=draft,
        hits=hits,
        rule_decision=rule_decision.value,
        rule_critique=[f"[{i.code.value}] {i.detail}" for i in rule_critique],
        processed_answer=processed_answer,
    )
    messages = [
        {"role": "system", "content": SAFETY_REVIEWER_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    try:
        response = await call_safety_reviewer(messages, temperature=0.0)
    except Exception as exc:
        print(f"  Warning: LLM safety review unavailable ({exc})")
        return None

    parsed = parse_llm_safety_response(response)
    if parsed is None:
        print("  Warning: LLM safety review returned unparseable JSON; using rules only.")
    return parsed
