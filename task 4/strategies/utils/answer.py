"""Normalize model outputs to gradable numeric strings."""

import re

_NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
_FINISH_RE = re.compile(r"finish\[\s*([^\]]+?)\s*\]", re.IGNORECASE)


def extract_finish_value(text: str) -> str:
    """Parse the value inside finish[...] if present."""
    match = _FINISH_RE.search(text or "")
    return match.group(1).strip() if match else ""


def normalize_numeric_answer(text: str) -> str:
    """
    Extract a single numeric string suitable for exact-match grading.
    Strips $, commas, units, and common answer prefixes.
    """
    if not text:
        return ""

    candidate = extract_finish_value(text) or text.strip()
    candidate = candidate.splitlines()[0].strip()
    candidate = candidate.replace(",", "").replace("$", "").replace("£", "")
    candidate = re.sub(
        r"^(?:answer|result|final answer)\s*[:=]\s*",
        "",
        candidate,
        flags=re.IGNORECASE,
    ).strip()

    if _NUMBER_RE.fullmatch(candidate):
        value = float(candidate)
        return str(int(value)) if value.is_integer() else candidate

    nums = re.findall(r"-?\d+(?:\.\d+)?", candidate)
    if nums:
        value = float(nums[-1])
        return str(int(value)) if value.is_integer() else nums[-1]

    return candidate.strip()
