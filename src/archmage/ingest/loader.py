"""Load Markdown knowledge files from the local corpus."""
from __future__ import annotations
from pathlib import Path
from typing import Iterable

from ..config import RAW_SESSIONS_DIR


def load_markdown_files(corpus_dir: Path | str = RAW_SESSIONS_DIR) -> list[tuple[str, str]]:
    """Return (relative_filename, text) for all recursive *.md files."""
    directory = Path(corpus_dir)
    if not directory.is_dir():
        return []
    loaded: list[tuple[str, str]] = []
    for path in sorted(directory.rglob("*.md")):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"Could not read corpus file {path}: {exc}") from exc
        loaded.append((str(path.relative_to(directory)), content))
    return loaded
