"""Application configuration and absolute project paths."""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
if not GEMINI_API_KEY or GEMINI_API_KEY == "replace_with_your_api_key":
    raise RuntimeError(
        "GEMINI_API_KEY is missing. Copy .env.example to .env and add your Google AI Studio API key."
    )

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip() or "gemini-3.8-flash"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 3
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

DATA_DIR = PROJECT_ROOT / "data"
RAW_SESSIONS_DIR = DATA_DIR / "raw" / "sessions"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
INDEX_PATH = EMBEDDINGS_DIR / "index.pkl"
LOGS_DIR = PROJECT_ROOT / "logs"
SESSION_LOGS_DIR = LOGS_DIR / "sessions"
AUDIT_LOG_DIR = LOGS_DIR / "audit"
SAFETY_RULES_PATH = RAW_SESSIONS_DIR / "safety-rules.md"
GAMES_DIR = Path.home() / "Games" / "cs16"
