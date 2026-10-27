from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
DEFAULT_DATABASE_PATH = BACKEND_ROOT / "data" / "mental_health.db"
load_dotenv(PROJECT_ROOT / ".env")


def database_path() -> Path:
    configured = os.getenv("MENTAL_HEALTH_DB_PATH", "").strip()
    if not configured:
        return DEFAULT_DATABASE_PATH
    path = Path(configured)
    return path if path.is_absolute() else BACKEND_ROOT.parent / path


def gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "").strip()


def gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip() or "gemini-3.5-flash-lite"

