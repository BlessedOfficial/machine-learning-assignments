import re
from pathlib import Path

from config import DOC_BASE_URL
from rag.access_control import min_role_for_document

_POLICY_ID_RE = re.compile(
    r"\*\*(?:Policy ID|Document ID):\*\*\s*(\S+)",
    re.IGNORECASE,
)
_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_URL_RE = re.compile(r"\*\*(?:URL|Canonical URL):\*\*\s*(\S+)", re.IGNORECASE)
_PAGE_RE = re.compile(r"\*\*(?:Page|Section page):\*\*\s*(\S+)", re.IGNORECASE)


def citation_fields_for_document(
    text: str,
    source_file: str,
    *,
    chunk_index: int = 0,
) -> dict[str, str]:
    """Extract citation metadata from a corpus markdown file."""
    policy_match = _POLICY_ID_RE.search(text)
    policy_id = policy_match.group(1).strip() if policy_match else ""

    section_match = _H1_RE.search(text)
    section = section_match.group(1).strip() if section_match else ""

    url_match = _URL_RE.search(text)
    if url_match:
        url = url_match.group(1).strip()
    else:
        stem = Path(source_file).stem
        url = f"{DOC_BASE_URL.rstrip('/')}/{stem}"

    page_match = _PAGE_RE.search(text)
    if page_match:
        page = page_match.group(1).strip()
    else:
        page = str(chunk_index + 1)

    return {
        "policy_id": policy_id,
        "section": section,
        "page": page,
        "url": url,
        "min_role": min_role_for_document(source_file),
    }
