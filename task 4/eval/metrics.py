import re


def normalize_answer(text: str) -> str:
    """Normalize GSM8K-style numeric answers for exact-match grading."""
    if text is None:
        return ""
    s = str(text).strip()
    # Take last line / token if model adds extra text
    if "\n" in s:
        s = s.strip().splitlines()[-1].strip()
    s = s.replace(",", "").replace("$", "").replace("%", "")
    s = re.sub(r"[^\d.\-]", "", s)
    if s.endswith("."):
        s = s[:-1]
    # 18.0 -> 18
    try:
        value = float(s)
        if value.is_integer():
            return str(int(value))
        return str(value)
    except ValueError:
        return s


def exact_match(prediction: str, ground_truth: str) -> bool:
    return normalize_answer(prediction) == normalize_answer(ground_truth)
