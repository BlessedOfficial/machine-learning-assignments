"""Input safety: prompt-injection detection, PII filtering, and scope checks."""

import re
from dataclasses import dataclass, field

from workflow.incident_log import log_guardrail_incident
from workflow.pii_utils import find_credit_card_spans, redact_pii
from workflow.prompts import OUT_OF_SCOPE_REPLY
from workflow.scope_filter import detect_scope_violation

from config import PII_ACTION

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


def guard_user_input(text: str) -> InputGuardResult:
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
        return result

    if detect_prompt_injection(original):
        result = InputGuardResult(
            allowed=False,
            text=original,
            block_message=OUT_OF_SCOPE_REPLY,
            rule_triggered="prompt_injection",
            prompt_injection=True,
        )
        _log_rejection(rule="prompt_injection", raw_input=original)
        return result

    scope_violation = detect_scope_violation(original)
    if scope_violation:
        rule = f"out_of_scope_{scope_violation}"
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

    if find_credit_card_spans(original):
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
            result = InputGuardResult(
                allowed=False,
                text=original,
                block_message=OUT_OF_SCOPE_REPLY,
                rule_triggered=rule,
                pii_detected=pii_flags,
            )
            _log_rejection(rule=rule, raw_input=original)
            return result

        return InputGuardResult(
            allowed=True,
            text=redacted,
            pii_detected=pii_flags,
            pii_redacted=True,
        )

    return InputGuardResult(allowed=True, text=original)
