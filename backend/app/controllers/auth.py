from __future__ import annotations

import secrets
from pathlib import Path

from app.controllers import database


_sessions: dict[str, str] = {}


def _issue(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    _sessions[token] = user_id
    return token


def register(database_path: Path, username: str, display_name: str, email: str | None, password: str) -> dict:
    user = database.create_user_account(database_path, username, display_name, email, password)
    return {"token": _issue(user["id"]), "user": user}


def login(database_path: Path, username: str, password: str) -> dict:
    user = database.authenticate_user(database_path, username, password)
    return {"token": _issue(user["id"]), "user": user}


def user_id_for_token(token: str) -> str:
    try:
        return _sessions[token]
    except KeyError as exc:
        raise database.AuthenticationError("Session is missing or expired") from exc


def logout(token: str) -> None:
    _sessions.pop(token, None)

