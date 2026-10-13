"""Build a local CPU sentence-transformer index and store it as a pickle."""
from __future__ import annotations

import pickle
import sys
import tempfile
from pathlib import Path

try:
    from ..config import EMBEDDING_MODEL, EMBEDDINGS_DIR, INDEX_PATH, RAW_SESSIONS_DIR
except RuntimeError as exc:
    print(f"Configuration error: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc
from .chunker import chunk_documents
from .loader import load_markdown_files


def build_index() -> Path:
    documents = load_markdown_files(RAW_SESSIONS_DIR)
    if not documents:
        raise RuntimeError(
            f"The corpus directory is empty: {RAW_SESSIONS_DIR}. Add Markdown files (*.md) and try again."
        )
    chunks = chunk_documents(documents)
    if not chunks:
        raise RuntimeError("Corpus files contain no non-empty text to embed.")

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers is not installed. Activate the virtual environment and run: pip install -r requirements.txt"
        ) from exc

    model = SentenceTransformer(EMBEDDING_MODEL, device="cpu")
    texts = [str(item["text"]) for item in chunks]
    vectors = model.encode(
        texts,
        batch_size=16,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    payload = {
        "version": 1,
        "model_name": EMBEDDING_MODEL,
        "chunks": chunks,
        "embeddings": vectors,
    }
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=EMBEDDINGS_DIR, prefix="index.", suffix=".tmp", delete=False
        ) as handle:
            temp_path = Path(handle.name)
            pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
            handle.flush()
        temp_path.replace(INDEX_PATH)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)
    print(f"Built index with {len(chunks)} chunks: {INDEX_PATH}")
    return INDEX_PATH


def main() -> int:
    try:
        build_index()
    except Exception as exc:
        print(f"Embedding build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
