import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def extract_python_code(raw: str) -> str:
    text = raw.strip()
    fence = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    return text


def run_python_code(code: str, *, timeout: float = 5.0) -> str:
    """Run generated Python in a subprocess; return stdout (final answer)."""
    cleaned = extract_python_code(code)
    if not cleaned:
        raise ValueError("No Python code to execute")

    fd, name = tempfile.mkstemp(suffix=".py")
    os.close(fd)
    path = Path(name)
    try:
        path.write_text(cleaned, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "execution failed").strip()
            raise RuntimeError(err)
        return result.stdout.strip()
    finally:
        path.unlink(missing_ok=True)
