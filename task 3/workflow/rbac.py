"""Role-based access control for retrieved chunks."""

from config import DEFAULT_USER_ROLE, ENABLE_RBAC
from rag.access_control import role_rank


def filter_hits_by_role(hits: list[dict], user_role: str | None) -> list[dict]:
    """
    Drop chunks whose min_role exceeds the caller's role.
    Chunks without min_role metadata default to employee-level access.
    """
    if not ENABLE_RBAC:
        return hits

    role = (user_role or DEFAULT_USER_ROLE).lower()
    user_level = role_rank(role)
    allowed: list[dict] = []
    for hit in hits:
        metadata = hit.get("metadata") or {}
        min_role = metadata.get("min_role") or hit.get("min_role") or "employee"
        if user_level >= role_rank(str(min_role)):
            allowed.append(hit)
    return allowed
