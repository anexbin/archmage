"""Top-k cosine retrieval over the locally embedded Markdown corpus."""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
except ImportError as exc:  # pragma: no cover - environment dependent
    raise RuntimeError("Local retrieval dependencies are missing. Activate the virtual environment and run: pip install -r requirements.txt") from exc

from ..config import EMBEDDING_MODEL, INDEX_PATH, TOP_K


class Retriever:
    def __init__(self, index_path: Path | str = INDEX_PATH) -> None:
        self.index_path = Path(index_path)
        if not self.index_path.is_file():
            raise FileNotFoundError(f"Embedding index not found: {self.index_path}")
        try:
            with self.index_path.open("rb") as handle:
                payload = pickle.load(handle)
        except (OSError, pickle.PickleError, EOFError) as exc:
            raise RuntimeError(f"Could not load embedding index {self.index_path}: {exc}") from exc
        if not isinstance(payload, dict) or "chunks" not in payload or "embeddings" not in payload:
            raise RuntimeError("Embedding index has an unexpected format. Rebuild it with python -m archmage.ingest.embedder.")
        self.chunks: list[dict[str, Any]] = payload["chunks"]
        self.embeddings = np.asarray(payload["embeddings"], dtype=np.float32)
        if len(self.chunks) == 0 or self.embeddings.ndim != 2 or self.embeddings.shape[0] != len(self.chunks):
            raise RuntimeError("Embedding index is empty or inconsistent. Rebuild it with python -m archmage.ingest.embedder.")
        self.model_name = str(payload.get("model_name", EMBEDDING_MODEL))
        if self.model_name != EMBEDDING_MODEL:
            raise RuntimeError(
                f"Index model is {self.model_name!r}, expected {EMBEDDING_MODEL!r}. Rebuild the index."
            )
        self.model = SentenceTransformer(EMBEDDING_MODEL, device="cpu")

    def retrieve(self, query: str, top_k: int = TOP_K) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        if top_k < 1:
            return []
        vector = self.model.encode(
            [query], convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
        )[0]
        scores = self.embeddings @ np.asarray(vector, dtype=np.float32)
        limit = min(top_k, len(self.chunks))
        best = np.argsort(scores)[::-1][:limit]
        results: list[dict[str, Any]] = []
        for idx in best:
            item = dict(self.chunks[int(idx)])
            item["score"] = float(scores[int(idx)])
            results.append(item)
        return results
