"""Character-based text chunking with a fixed overlap."""
from __future__ import annotations
from typing import Iterable

from ..config import CHUNK_OVERLAP, CHUNK_SIZE


def chunk_documents(
    documents: Iterable[tuple[str, str]],
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict[str, object]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be at least 0 and smaller than chunk_size")
    chunks: list[dict[str, object]] = []
    step = chunk_size - overlap
    for source, text in documents:
        text = text.strip()
        if not text:
            continue
        chunk_index = 0
        for start in range(0, len(text), step):
            piece = text[start : start + chunk_size].strip()
            if piece:
                chunks.append({"text": piece, "source": source, "chunk_index": chunk_index})
                chunk_index += 1
            if start + chunk_size >= len(text):
                break
    return chunks
