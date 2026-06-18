"""Input safety: prompt-injection detection, PII filtering, and scope checks."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from config import ENABLE_LLM_INPUT_REVIEW, PII_ACTION
from workflow.incident_log import log_guardrail_incident
from workflow.pii_utils import find_credit_card_spans, redact_pii
from workflow.prompts import OUT_OF_SCOPE_REPLY
from workflow.scope_filter import detect_scope_violation

if TYPE_CHECKING:
    from agents.pipeline_console import PipelineConsole

_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions",
        r"disregard\s+(?:all\s+)?(?:previous|prior|your)\s+instructions",
        r"forget\s+(?:everything|all)\s+(?:you\s+)?(?:were\s+)?(?:told|instructed)",
        r"override\s+(?:your\s+)?(?:instructions|rules|guidelines)",
        r"reveal\s+(?:your\s+)?(?:system\s+)?prompt",
        r"show\s+(?:me\s+)?(?:your\s+)?(?:system\s+)?prompt",
        r"print\s+(?:your\s+)?(?:system\s+)?prompt",
        r"what\s+(?:is|are)\s+your\s+(?:system\s+)?(?:prompt|instructions)",
        r"repeat\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions)",
        r"you\s+are\s+now\s+(?:a|an|in)\s+",
        r"act\s+as\s+(?:if\s+you\s+are|a|an)\s+",
        r"pretend\s+(?:you\s+are|to\s+be)\s+",
        r"role[\s-]?play\s+as\s+",
        r"jailbreak",
        r"\bDAN\s+mode\b",
        r"developer\s+mode\s+enabled",
        r"new\s+instructions\s*:",
        r"<\s*/?\s*(?:system|assistant|instruction)\s*>",
        r"sudo\s+mode",
        r"bypass\s+(?:your\s+)?(?:safety|guardrails|restrictions|filters)",
    )
)


@dataclass
class InputGuardResult:
    allowed: bool
    text: str
    block_message: str | None = None
    rule_triggered: str | None = None
    prompt_injection: bool = False
    out_of_scope: bool = False
    scope_violation: str | None = None
    pii_detected: list[str] = field(default_factory=list)
    pii_redacted: bool = False
    llm_reviewed: bool = False
    llm_decision: str | None = None
    llm_issues: list[str] = field(default_factory=list)


def detect_prompt_injection(text: str) -> bool:
    return any(pattern.search(text) for pattern in _INJECTION_PATTERNS)


def rule_triggered_for_result(result: InputGuardResult) -> str | None:
    if result.rule_triggered:
        return result.rule_triggered
    if result.prompt_injection:
        return "prompt_injection"
    if result.out_of_scope and result.scope_violation:
        return f"out_of_scope_{result.scope_violation}"
    if result.pii_detected:
        if "credit_card" in result.pii_detected:
            return "pii_credit_card"
        return "pii_" + "_".join(result.pii_detected)
    return None


def input_guard_decision(result: InputGuardResult) -> str:
    """Return pass, redact, or reject for pipeline logging."""
    if not result.allowed:
        return "reject"
    if result.pii_redacted:
        return "redact"
    return "pass"


def _log_rejection(*, rule: str, raw_input: str, detail: str | None = None) -> None:
    log_guardrail_incident(
        rule_triggered=rule,
        raw_input=raw_input,
        decision="block",
        stage="input",
        detail=detail,
    )


def guard_user_input(
    text: str,
    *,
    console: PipelineConsole | None = None,
) -> InputGuardResult:
    """Run input guardrails before retrieval / LLM calls."""
    original = (text or "").strip()
    if not original:
        result = InputGuardResult(
            allowed=False,
            text="",
            block_message=OUT_OF_SCOPE_REPLY,
            rule_triggered="empty_input",
        )
        _log_rejection(rule="empty_input", raw_input=text or "")
        if console:
            console.header("Guardrail", "Input guard - deterministic rules")
            console.step("Guardrail", "empty input check", result="REJECT")
        return result

    if console:
        console.header("Guardrail", "Input guard - deterministic rules")

    if detect_prompt_injection(original):
        if console:
            console.step("Guardrail", "prompt-injection detection", result="REJECT")
        result = InputGuardResult(
            allowed=False,
            text=original,
            block_message=OUT_OF_SCOPE_REPLY,
            rule_triggered="prompt_injection",
            prompt_injection=True,
        )
        _log_rejection(rule="prompt_injection", raw_input=original)
        return result
    if console:
        console.step("Guardrail", "prompt-injection detection", result="PASS")

    scope_violation = detect_scope_violation(original)
    if scope_violation:
        rule = f"out_of_scope_{scope_violation}"
        if console:
            console.step(
                "Guardrail",
                "topic / policy filter",
                result="REJECT",
                detail=scope_violation,
            )
        result = InputGuardResult(
            allowed=False,
            text=original,
            block_message=OUT_OF_SCOPE_REPLY,
            rule_triggered=rule,
            out_of_scope=True,
            scope_violation=scope_violation,
        )
        _log_rejection(rule=rule, raw_input=original, detail=scope_violation)
        return result
    if console:
        console.step("Guardrail", "topic / policy filter", result="PASS")

    if find_credit_card_spans(original):
        if console:
            console.step("Guardrail", "PII scan (credit card)", result="REJECT")
        result = InputGuardResult(
            allowed=False,
            text=original,
            block_message=OUT_OF_SCOPE_REPLY,
            rule_triggered="pii_credit_card",
            pii_detected=["credit_card"],
        )
        _log_rejection(rule="pii_credit_card", raw_input=original)
        return result

    redacted, pii_flags = redact_pii(original, allow_corporate_email=False)
    if pii_flags:
        if PII_ACTION == "refuse":
            rule = "pii_" + "_".join(pii_flags)
            if console:
                console.step(
                    "Guardrail",
                    "PII scan",
                    result="REJECT",
                    detail=",".join(pii_flags),
                )
            result = InputGuardResult(
                allowed=False,
                text=original,
                block_message=OUT_OF_SCOPE_REPLY,
                rule_triggered=rule,
                pii_detected=pii_flags,
            )
            _log_rejection(rule=rule, raw_input=original)
            return result

        if console:
            console.step(
                "Guardrail",
                "PII scan",
                result="REDACT",
                detail=",".join(pii_flags),
            )
        return InputGuardResult(
            allowed=True,
            text=redacted,
            pii_detected=pii_flags,
            pii_redacted=True,
        )

    if console:
        console.step("Guardrail", "PII scan", result="PASS")
    return InputGuardResult(allowed=True, text=original)


async def guard_user_input_hybrid(
    text: str,
    *,
    console: PipelineConsole | None = None,
) -> InputGuardResult:
    """
    Deterministic rules first; optional LLM reviewer tightens only.
    """
    rule_result = guard_user_input(text, console=console)

    if not rule_result.allowed:
        return rule_result

    if not ENABLE_LLM_INPUT_REVIEW:
        return rule_result

    from llms.input_guard_reviewer.review import run_llm_input_guard_review

    llm_review = await run_llm_input_guard_review(rule_result.text, rule_result)
    if llm_review is None:
        return rule_result

    rule_result.llm_reviewed = True
    rule_result.llm_decision = llm_review.decision
    rule_result.llm_issues = [
        f"[{i['code']}] {i['detail']}" for i in llm_review.issues
    ]

    if console:
        console.header("Guardrail", "Input guard - LLM reviewer")
        detail = "; ".join(rule_result.llm_issues) if rule_result.llm_issues else None

    if llm_review.decision == "block":
        rule = llm_review.primary_rule or "llm_input_block"
        if console:
            console.step(
                "Guardrail",
                "hybrid LLM review",
                result="REJECT",
                detail=detail,
            )
        log_guardrail_incident(
            rule_triggered=rule,
            raw_input=text,
            decision="block",
            stage="input",
            detail=detail,
        )
        return InputGuardResult(
            allowed=False,
            text=rule_result.text,
            block_message=OUT_OF_SCOPE_REPLY,
            rule_triggered=rule,
            pii_detected=list(rule_result.pii_detected),
            pii_redacted=rule_result.pii_redacted,
            llm_reviewed=True,
            llm_decision="block",
            llm_issues=rule_result.llm_issues,
        )

    if llm_review.decision == "redact" and llm_review.sanitized_question:
        sanitized = llm_review.sanitized_question
        sanitized, extra_flags = redact_pii(sanitized, allow_corporate_email=False)
        merged_flags = list(dict.fromkeys([*rule_result.pii_detected, *extra_flags]))
        if console:
            console.step(
                "Guardrail",
                "hybrid LLM review",
                result="REDACT",
                detail=detail,
            )
        if extra_flags or llm_review.issues:
            log_guardrail_incident(
                rule_triggered=llm_review.primary_rule or "llm_input_redact",
                raw_input=text,
                decision="redact",
                stage="input",
                detail=detail,
            )
        return InputGuardResult(
            allowed=True,
            text=sanitized,
            pii_detected=merged_flags,
            pii_redacted=True,
            llm_reviewed=True,
            llm_decision="redact",
            llm_issues=rule_result.llm_issues,
        )

    if console:
        console.step("Guardrail", "hybrid LLM review", result="PASS", detail=detail)
    return rule_result
