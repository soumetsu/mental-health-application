from __future__ import annotations

import tempfile
import unittest
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path

from app.controllers import database


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.database_path = Path(self.temp_directory.name) / "test.db"
        database.initialize_database(self.database_path)
        self.user = database.create_user_account(
            self.database_path, "river", "River", "river@example.test", "password123"
        )

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_authentication_and_unique_account(self) -> None:
        authenticated = database.authenticate_user(self.database_path, "RIVER", "password123")
        self.assertEqual(authenticated["id"], self.user["id"])
        with self.assertRaises(database.AuthenticationError):
            database.authenticate_user(self.database_path, "river", "wrong password")
        with self.assertRaises(database.AccountConflictError):
            database.create_user_account(self.database_path, "river", "Other", None, "password123")

    def test_questionnaire_checkin_event_and_dashboard(self) -> None:
        questionnaire = database.save_questionnaire(
            self.database_path,
            self.user["id"],
            {"stressors": ["school"], "sleep_hours": 7.5, "support_style": "balanced"},
        )
        self.assertEqual(questionnaire["stressors"], ["school"])

        database.create_checkin(
            self.database_path,
            self.user["id"],
            {"mood": 2, "energy": 3, "note": "A demanding day", "tags": ["school"]},
        )
        event = database.create_event(
            self.database_path,
            self.user["id"],
            {"title": "Finished an assignment", "details": "", "valence": "positive", "intensity": 3, "happened_on": date.today()},
        )

        snapshot = database.dashboard_snapshot(self.database_path, self.user["id"])
        self.assertTrue(snapshot["today_check_in_complete"])
        self.assertEqual(snapshot["today_event_count"], 1)
        self.assertIn(snapshot["support_state"], {"support", "gentle", "steady", "calm"})
        self.assertNotIn("score", snapshot)

        database.delete_event(self.database_path, self.user["id"], event["id"])
        self.assertEqual(database.list_events(self.database_path, self.user["id"]), [])

    def test_records_are_scoped_to_user(self) -> None:
        other = database.create_user_account(self.database_path, "sky", "Sky", None, "password123")
        database.create_event(
            self.database_path,
            self.user["id"],
            {"title": "Private", "details": "", "valence": "neutral", "intensity": 1, "happened_on": date.today()},
        )
        self.assertEqual(database.list_events(self.database_path, other["id"]), [])

    def test_saved_chat_is_bounded_ordered_and_scoped(self) -> None:
        river = self.user["id"]
        sky = database.create_user_account(self.database_path, "sky", "Sky", None, "password123")["id"]
        database.save_chat_turn(self.database_path, sky, "Sky's message", "Sky's reply")
        for number in range(database.CHAT_TURN_LIMIT + 2):
            database.save_chat_turn(self.database_path, river, f"Message {number}", f"Reply {number}")
        database.initialize_database(self.database_path)
        history = database.list_chat_turns(self.database_path, river)
        self.assertEqual(len(history), database.CHAT_TURN_LIMIT)
        self.assertEqual(history[0], {"message": "Message 2", "reply": "Reply 2"})
        self.assertEqual(history[-1]["message"], f"Message {database.CHAT_TURN_LIMIT + 1}")
        database.clear_chat_turns(self.database_path, river)
        self.assertEqual(database.list_chat_turns(self.database_path, river), [])
        self.assertEqual(database.list_chat_turns(self.database_path, sky), [
            {"message": "Sky's message", "reply": "Sky's reply"},
        ])

    def test_exercise_history_crud_counts_hidden_duration(self) -> None:
        entry = database.create_exercise_history(
            self.database_path, self.user["id"], "grounding-54321"
        )
        self.assertEqual(entry["status"], "in_progress")
        self.assertNotIn("duration_seconds", entry)

        updated = database.update_exercise_history(
            self.database_path,
            self.user["id"],
            entry["id"],
            "completed",
            "Helped me notice the room.",
        )
        self.assertEqual(updated["status"], "completed")
        self.assertEqual(updated["reflection"], "Helped me notice the room.")
        self.assertNotIn("duration_seconds", updated)

        with closing(sqlite3.connect(self.database_path)) as connection:
            duration = connection.execute(
                "SELECT duration_seconds FROM exercise_history WHERE id = ?", (entry["id"],)
            ).fetchone()[0]
        self.assertIsInstance(duration, int)
        self.assertGreaterEqual(duration, 0)

        history = database.list_exercise_history(self.database_path, self.user["id"])
        self.assertEqual([item["id"] for item in history], [entry["id"]])
        database.delete_exercise_history(self.database_path, self.user["id"], entry["id"])
        self.assertEqual(database.list_exercise_history(self.database_path, self.user["id"]), [])


if __name__ == "__main__":
    unittest.main()
