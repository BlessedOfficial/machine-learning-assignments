"""Shared PII detection and redaction."""

import re

_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
_PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?\d{1,3}[\s.-]?)?"
    r"(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)"
)
_SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CREDIT_CARD_CANDIDATE = re.compile(
    r"\b(?:\d[\s-]?){13,19}\d\b"
)

_CORPORATE_EMAIL_SUFFIXES = ("@ai.inc", "@benefits.ai.inc")


def _luhn_valid(digits: str) -> bool:
    if not digits.isdigit() or len(digits) < 13:
        return False
    total = 0
    reverse = digits[::-1]
    for index, char in enumerate(reverse):
        n = int(char)
        if index % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def find_credit_card_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for match in _CREDIT_CARD_CANDIDATE.finditer(text):
        digits = re.sub(r"\D", "", match.group())
        if 13 <= len(digits) <= 19 and _luhn_valid(digits):
            spans.append(match.span())
    return spans


def _redact_emails(text: str, *, allow_corporate: bool) -> tuple[str, bool]:
    changed = False

    def repl(match: re.Match[str]) -> str:
        nonlocal changed
        email = match.group(0)
        if allow_corporate and email.lower().endswith(_CORPORATE_EMAIL_SUFFIXES):
            return email
        changed = True
        return "[REDACTED_EMAIL]"

    return _EMAIL_PATTERN.sub(repl, text), changed


def redact_pii(text: str, *, allow_corporate_email: bool = False) -> tuple[str, list[str]]:
    """Redact email, phone, SSN. Optionally preserve @ai.inc contact addresses."""
    flags: list[str] = []
    redacted = text

    redacted, email_changed = _redact_emails(
        redacted, allow_corporate=allow_corporate_email
    )
    if email_changed:
        flags.append("email")

    for label, pattern, token in (
        ("phone", _PHONE_PATTERN, "[REDACTED_PHONE]"),
        ("ssn", _SSN_PATTERN, "[REDACTED_SSN]"),
    ):
        if pattern.search(redacted):
            flags.append(label)
            redacted = pattern.sub(token, redacted)

    return redacted, flags


def redact_leaked_pii(text: str) -> tuple[str, list[str]]:
    """Redact PII in model output; keep published AI.Inc contact emails."""
    redacted, flags = redact_pii(text, allow_corporate_email=True)
    if find_credit_card_spans(redacted):
        flags.append("credit_card")
        redacted = _CREDIT_CARD_CANDIDATE.sub("[REDACTED_PAYMENT]", redacted)
    return redacted, flags


def _extract_pii_spans(text: str) -> list[tuple[str, str]]:
    """Return (kind, matched_text) for cross-leak detection."""
    spans: list[tuple[str, str]] = []
    for match in _EMAIL_PATTERN.finditer(text):
        email = match.group(0)
        if not email.lower().endswith(_CORPORATE_EMAIL_SUFFIXES):
            spans.append(("email", email))
    for match in _PHONE_PATTERN.finditer(text):
        spans.append(("phone", match.group(0)))
    for match in _SSN_PATTERN.finditer(text):
        spans.append(("ssn", match.group(0)))
    for start, end in find_credit_card_spans(text):
        spans.append(("credit_card", text[start:end]))
    return spans


def _redact_span_in_text(text: str, span: str, kind: str) -> str:
    token = {
        "email": "[REDACTED_EMAIL]",
        "phone": "[REDACTED_PHONE]",
        "ssn": "[REDACTED_SSN]",
        "credit_card": "[REDACTED_PAYMENT]",
    }.get(kind, "[REDACTED]")
    return text.replace(span, token)


def redact_output_pii(
    draft: str,
    hits: list[dict],
    *,
    source_input: str = "",
) -> tuple[str, list[str]]:
    """
    Scan retrieved chunks and draft response; redact PII before delivery.
    """
    from workflow.incident_log import log_guardrail_incident

    merged_flags: list[str] = []
    chunk_spans: list[tuple[str, str]] = []

    for hit in hits:
        chunk_text = str(hit.get("text") or "")
        chunk_id = str(hit.get("chunk_id") or "unknown")
        _, chunk_flags = redact_pii(chunk_text, allow_corporate_email=True)
        if find_credit_card_spans(chunk_text):
            chunk_flags = list(dict.fromkeys([*chunk_flags, "credit_card"]))
        if chunk_flags:
            log_guardrail_incident(
                rule_triggered="pii_in_retrieved_chunk",
                raw_input=source_input or draft[:500],
                decision="block",
                stage="output",
                detail=f"chunk_id={chunk_id}; flags={','.join(chunk_flags)}",
            )
            for flag in chunk_flags:
                if flag not in merged_flags:
                    merged_flags.append(flag)
        chunk_spans.extend(_extract_pii_spans(chunk_text))

    redacted, draft_flags = redact_leaked_pii(draft)
    for flag in draft_flags:
        if flag not in merged_flags:
            merged_flags.append(flag)

    for kind, span in chunk_spans:
        if span and span in redacted:
            redacted = _redact_span_in_text(redacted, span, kind)
            if kind not in merged_flags:
                merged_flags.append(kind)

    return redacted, merged_flags
