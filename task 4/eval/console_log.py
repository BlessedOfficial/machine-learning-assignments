"""Mirror stdout to a log file while eval runs."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, TextIO


class _TeeStream:
    def __init__(self, *streams: TextIO):
        self._streams = streams

    def write(self, data: str) -> int:
        for stream in self._streams:
            stream.write(data)
            stream.flush()
        return len(data)

    def flush(self) -> None:
        for stream in self._streams:
            stream.flush()

    def isatty(self) -> bool:
        return self._streams[0].isatty()


@contextmanager
def tee_console(log_path: Path) -> Iterator[Path]:
    """Write all stdout to log_path in addition to the terminal."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log_file:
        original = sys.stdout
        sys.stdout = _TeeStream(original, log_file)
        try:
            yield log_path
        finally:
            sys.stdout = original
