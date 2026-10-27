from __future__ import annotations

import os
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_PATH = BACKEND_ROOT / "data" / "mental_health.db"


def database_path() -> Path:
    configured = os.getenv("MENTAL_HEALTH_DB_PATH", "").strip()
    if not configured:
        return DEFAULT_DATABASE_PATH
    path = Path(configured)
    return path if path.is_absolute() else BACKEND_ROOT.parent / path

