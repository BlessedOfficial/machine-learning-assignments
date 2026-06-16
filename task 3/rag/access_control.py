"""Document-level minimum role for RBAC filtering."""

from pathlib import Path

# Default access for all corpus docs unless listed below.
DEFAULT_MIN_ROLE = "employee"

# Manager-only internal policies (demo RBAC labels).
DOCUMENT_MIN_ROLE: dict[str, str] = {
    "business-travel-policy.md": "manager",
    "expense-reimbursement.md": "manager",
    "security-incident-response.md": "manager",
    "data-classification-policy.md": "manager",
    "confidentiality-nda-policy.md": "hr",
}

ROLE_RANK: dict[str, int] = {
    "intern": 1,
    "employee": 1,
    "manager": 2,
    "hr": 3,
    "admin": 4,
}


def min_role_for_document(source_file: str) -> str:
    name = Path(source_file).name
    return DOCUMENT_MIN_ROLE.get(name, DEFAULT_MIN_ROLE)


def role_rank(role: str) -> int:
    return ROLE_RANK.get(role.lower(), ROLE_RANK[DEFAULT_MIN_ROLE])
