from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Iterator

from app.controllers.security import hash_password, verify_password


class DataAccessError(RuntimeError):
    pass


class AccountConflictError(DataAccessError):
    pass


class AuthenticationError(DataAccessError):
    pass


class NotFoundError(DataAccessError):
    pass


def _now() -> str:
    return datetime.now(UTC).isoformat()


@contextmanager
def _connect(database_path: Path) -> Iterator[sqlite3.Connection]:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


def initialize_database(database_path: Path) -> None:
    schema = """
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT NOT NULL UNIQUE COLLATE NOCASE,
        display_name TEXT NOT NULL,
        email TEXT UNIQUE COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS questionnaires (
        user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        stressors_json TEXT NOT NULL,
        sleep_hours REAL NOT NULL CHECK (sleep_hours BETWEEN 0 AND 24),
        support_style TEXT NOT NULL CHECK (support_style IN ('quiet', 'balanced', 'encouraging')),
        updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS check_ins (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        mood INTEGER NOT NULL CHECK (mood BETWEEN 1 AND 5),
        energy INTEGER NOT NULL CHECK (energy BETWEEN 1 AND 5),
        note TEXT NOT NULL,
        tags_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        details TEXT NOT NULL,
        valence TEXT NOT NULL CHECK (valence IN ('positive', 'negative', 'neutral')),
        intensity INTEGER NOT NULL CHECK (intensity BETWEEN 1 AND 5),
        happened_on TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS exercise_history (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        exercise_id TEXT NOT NULL CHECK (exercise_id IN ('grounding-54321', 'box-breathing')),
        status TEXT NOT NULL CHECK (status IN ('in_progress', 'completed', 'stopped')),
        reflection TEXT NOT NULL DEFAULT '',
        started_at TEXT NOT NULL,
        completed_at TEXT,
        duration_seconds INTEGER CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_check_ins_user_created ON check_ins(user_id, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_events_user_date ON events(user_id, happened_on DESC, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_exercise_history_user_started ON exercise_history(user_id, started_at DESC);
    """
    try:
        with _connect(database_path) as connection:
            connection.executescript(schema)
            connection.commit()
    except sqlite3.Error as exc:
        raise DataAccessError("Could not initialize local data") from exc


def _user_response(row: sqlite3.Row, has_questionnaire: bool) -> dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "email": row["email"],
        "has_questionnaire": has_questionnaire,
    }


def create_user_account(
    database_path: Path, username: str, display_name: str, email: str | None, password: str
) -> dict:
    user_id = uuid.uuid4().hex
    try:
        with _connect(database_path) as connection:
            connection.execute(
                "INSERT INTO users (id, username, display_name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username, display_name, email, hash_password(password), _now()),
            )
            connection.commit()
            row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return _user_response(row, False)
    except sqlite3.IntegrityError as exc:
        raise AccountConflictError("That username or email is already in use") from exc
    except sqlite3.Error as exc:
        raise DataAccessError("Could not create the account") from exc


def get_user(database_path: Path, user_id: str) -> dict:
    try:
        with _connect(database_path) as connection:
            row = connection.execute(
                """SELECT u.*, EXISTS(SELECT 1 FROM questionnaires q WHERE q.user_id = u.id) AS has_questionnaire
                   FROM users u WHERE u.id = ?""",
                (user_id,),
            ).fetchone()
            if not row:
                raise AuthenticationError("Session user was not found")
            return _user_response(row, bool(row["has_questionnaire"]))
    except sqlite3.Error as exc:
        raise DataAccessError("Could not read the account") from exc


def authenticate_user(database_path: Path, username: str, password: str) -> dict:
    try:
        with _connect(database_path) as connection:
            row = connection.execute(
                """SELECT u.*, EXISTS(SELECT 1 FROM questionnaires q WHERE q.user_id = u.id) AS has_questionnaire
                   FROM users u WHERE username = ? COLLATE NOCASE""",
                (username,),
            ).fetchone()
            if not row or not verify_password(password, row["password_hash"]):
                raise AuthenticationError("Username or password is incorrect")
            return _user_response(row, bool(row["has_questionnaire"]))
    except sqlite3.Error as exc:
        raise DataAccessError("Could not authenticate the account") from exc


def save_questionnaire(database_path: Path, user_id: str, data: dict) -> dict:
    updated_at = _now()
    try:
        with _connect(database_path) as connection:
            connection.execute(
                """INSERT INTO questionnaires (user_id, stressors_json, sleep_hours, support_style, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                     stressors_json = excluded.stressors_json,
                     sleep_hours = excluded.sleep_hours,
                     support_style = excluded.support_style,
                     updated_at = excluded.updated_at""",
                (user_id, json.dumps(data["stressors"]), data["sleep_hours"], data["support_style"], updated_at),
            )
            connection.commit()
        return {**data, "updated_at": updated_at}
    except sqlite3.Error as exc:
        raise DataAccessError("Could not save the questionnaire") from exc


def get_questionnaire(database_path: Path, user_id: str) -> dict | None:
    try:
        with _connect(database_path) as connection:
            row = connection.execute("SELECT * FROM questionnaires WHERE user_id = ?", (user_id,)).fetchone()
            if not row:
                return None
            return {
                "stressors": json.loads(row["stressors_json"]),
                "sleep_hours": row["sleep_hours"],
                "support_style": row["support_style"],
                "updated_at": row["updated_at"],
            }
    except (sqlite3.Error, json.JSONDecodeError) as exc:
        raise DataAccessError("Could not read the questionnaire") from exc


def _checkin_response(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "mood": row["mood"],
        "energy": row["energy"],
        "note": row["note"],
        "tags": json.loads(row["tags_json"]),
        "created_at": row["created_at"],
    }


def create_checkin(database_path: Path, user_id: str, data: dict) -> dict:
    checkin_id = uuid.uuid4().hex
    created_at = _now()
    try:
        with _connect(database_path) as connection:
            connection.execute(
                "INSERT INTO check_ins (id, user_id, mood, energy, note, tags_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (checkin_id, user_id, data["mood"], data["energy"], data["note"], json.dumps(data["tags"]), created_at),
            )
            connection.commit()
        return {"id": checkin_id, **data, "created_at": created_at}
    except sqlite3.Error as exc:
        raise DataAccessError("Could not save the check-in") from exc


def list_checkins(database_path: Path, user_id: str, limit: int = 30) -> list[dict]:
    try:
        with _connect(database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM check_ins WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
            return [_checkin_response(row) for row in rows]
    except (sqlite3.Error, json.JSONDecodeError) as exc:
        raise DataAccessError("Could not read check-ins") from exc


def _event_response(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "details": row["details"],
        "valence": row["valence"],
        "intensity": row["intensity"],
        "happened_on": row["happened_on"],
        "created_at": row["created_at"],
    }


def create_event(database_path: Path, user_id: str, data: dict) -> dict:
    event_id = uuid.uuid4().hex
    created_at = _now()
    try:
        with _connect(database_path) as connection:
            connection.execute(
                """INSERT INTO events (id, user_id, title, details, valence, intensity, happened_on, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_id, user_id, data["title"], data["details"], data["valence"], data["intensity"], str(data["happened_on"]), created_at),
            )
            connection.commit()
        return {"id": event_id, **data, "created_at": created_at}
    except sqlite3.Error as exc:
        raise DataAccessError("Could not save the event") from exc


def list_events(database_path: Path, user_id: str, month: str | None = None, limit: int = 100) -> list[dict]:
    sql = "SELECT * FROM events WHERE user_id = ?"
    params: list[object] = [user_id]
    if month:
        sql += " AND substr(happened_on, 1, 7) = ?"
        params.append(month)
    sql += " ORDER BY happened_on DESC, created_at DESC LIMIT ?"
    params.append(limit)
    try:
        with _connect(database_path) as connection:
            rows = connection.execute(sql, params).fetchall()
            return [_event_response(row) for row in rows]
    except sqlite3.Error as exc:
        raise DataAccessError("Could not read events") from exc


def delete_event(database_path: Path, user_id: str, event_id: str) -> None:
    try:
        with _connect(database_path) as connection:
            result = connection.execute("DELETE FROM events WHERE id = ? AND user_id = ?", (event_id, user_id))
            if result.rowcount == 0:
                raise NotFoundError("Event was not found")
            connection.commit()
    except sqlite3.Error as exc:
        raise DataAccessError("Could not delete the event") from exc


EXERCISE_TITLES = {
    "grounding-54321": "5-4-3-2-1 grounding",
    "box-breathing": "Four-count breathing",
}


def _exercise_history_response(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "exercise_id": row["exercise_id"],
        "exercise_title": EXERCISE_TITLES[row["exercise_id"]],
        "status": row["status"],
        "reflection": row["reflection"],
        "started_at": row["started_at"],
        "completed_at": row["completed_at"],
        "updated_at": row["updated_at"],
    }


def create_exercise_history(database_path: Path, user_id: str, exercise_id: str) -> dict:
    if exercise_id not in EXERCISE_TITLES:
        raise DataAccessError("Exercise is not supported")
    history_id = uuid.uuid4().hex
    now = _now()
    try:
        with _connect(database_path) as connection:
            connection.execute(
                """INSERT INTO exercise_history
                   (id, user_id, exercise_id, status, reflection, started_at, created_at, updated_at)
                   VALUES (?, ?, ?, 'in_progress', '', ?, ?, ?)""",
                (history_id, user_id, exercise_id, now, now, now),
            )
            connection.commit()
            row = connection.execute("SELECT * FROM exercise_history WHERE id = ?", (history_id,)).fetchone()
            return _exercise_history_response(row)
    except sqlite3.Error as exc:
        raise DataAccessError("Could not start the exercise") from exc


def list_exercise_history(database_path: Path, user_id: str, limit: int = 50) -> list[dict]:
    try:
        with _connect(database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM exercise_history WHERE user_id = ? ORDER BY started_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
            return [_exercise_history_response(row) for row in rows]
    except sqlite3.Error as exc:
        raise DataAccessError("Could not read exercise history") from exc


def update_exercise_history(
    database_path: Path,
    user_id: str,
    history_id: str,
    status: str | None,
    reflection: str | None,
) -> dict:
    now = _now()
    try:
        with _connect(database_path) as connection:
            row = connection.execute(
                "SELECT * FROM exercise_history WHERE id = ? AND user_id = ?",
                (history_id, user_id),
            ).fetchone()
            if not row:
                raise NotFoundError("Exercise history entry was not found")

            next_status = status or row["status"]
            next_reflection = row["reflection"] if reflection is None else reflection
            completed_at = row["completed_at"]
            duration_seconds = row["duration_seconds"]
            if status in {"completed", "stopped"} and row["status"] == "in_progress":
                completed_at = now
                started = datetime.fromisoformat(row["started_at"])
                duration_seconds = max(0, int((datetime.fromisoformat(now) - started).total_seconds()))

            connection.execute(
                """UPDATE exercise_history
                   SET status = ?, reflection = ?, completed_at = ?, duration_seconds = ?, updated_at = ?
                   WHERE id = ? AND user_id = ?""",
                (next_status, next_reflection, completed_at, duration_seconds, now, history_id, user_id),
            )
            connection.commit()
            updated = connection.execute("SELECT * FROM exercise_history WHERE id = ?", (history_id,)).fetchone()
            return _exercise_history_response(updated)
    except sqlite3.Error as exc:
        raise DataAccessError("Could not update exercise history") from exc


def delete_exercise_history(database_path: Path, user_id: str, history_id: str) -> None:
    try:
        with _connect(database_path) as connection:
            result = connection.execute(
                "DELETE FROM exercise_history WHERE id = ? AND user_id = ?",
                (history_id, user_id),
            )
            if result.rowcount == 0:
                raise NotFoundError("Exercise history entry was not found")
            connection.commit()
    except sqlite3.Error as exc:
        raise DataAccessError("Could not delete exercise history") from exc


def dashboard_snapshot(database_path: Path, user_id: str) -> dict:
    user = get_user(database_path, user_id)
    checkins = list_checkins(database_path, user_id, 30)
    events = list_events(database_path, user_id, limit=100)
    today = date.today()
    cutoff = today - timedelta(days=7)
    recent_moods = [item["mood"] for item in checkins if datetime.fromisoformat(str(item["created_at"])).date() >= cutoff]
    base = sum(recent_moods) / len(recent_moods) if recent_moods else 3.5
    recent_events = [item for item in events if date.fromisoformat(str(item["happened_on"])) >= cutoff]
    event_adjustment = sum(
        (0.08 * item["intensity"] if item["valence"] == "positive" else -0.1 * item["intensity"] if item["valence"] == "negative" else 0)
        for item in recent_events
    )
    score = max(1, min(5, base + event_adjustment))

    if score < 2.4:
        state, message, exercise = "support", "Today may feel heavy. We can keep this small and gentle.", "grounding-54321"
    elif score < 3.3:
        state, message, exercise = "gentle", "A little extra care could help today. You choose the pace.", "box-breathing"
    elif score < 4.2:
        state, message, exercise = "steady", "You are checking in with yourself. That is enough for this moment.", "grounding-54321"
    else:
        state, message, exercise = "calm", "Things seem steadier. The app will stay quietly available.", "box-breathing"

    today_text = today.isoformat()
    return {
        "display_name": user["display_name"],
        "support_state": state,
        "message": message,
        "affirmation": "Your experience is real, and you can take the next step one moment at a time.",
        "recommended_exercise_id": exercise,
        "today_check_in_complete": any(str(item["created_at"])[:10] == today_text for item in checkins),
        "today_event_count": sum(1 for item in events if str(item["happened_on"]) == today_text),
        "recent_events": events[:6],
    }

