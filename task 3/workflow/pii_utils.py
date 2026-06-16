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
