import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import BASELINE_PATH


def save_baseline(results: dict[str, Any], path: Path | None = None) -> Path:
    path = Path(path or BASELINE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        **results,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_baseline(path: Path | None = None) -> dict[str, Any] | None:
    path = Path(path or BASELINE_PATH)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def diff_against_baseline(
    current: dict[str, float],
    baseline: dict[str, Any],
) -> dict[str, float]:
    """Return accuracy deltas per strategy vs stored baseline."""
    base = baseline.get("strategies", baseline)
    return {name: current[name] - base[name] for name in current if name in base}
