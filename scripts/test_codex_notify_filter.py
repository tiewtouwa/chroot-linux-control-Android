import json
from pathlib import Path
import tempfile
import unittest

from codex_notify_filter import should_notify


class CodexNotifyFilterTest(unittest.TestCase):
    ROOT_ID = "00000000-0000-4000-8000-000000000001"
    CHILD_ID = "00000000-0000-4000-8000-000000000002"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)

    def metadata(self, thread_id, source):
        return {"type": "session_meta", "payload": {"id": thread_id, "source": source}}

    def write_rollout(self, thread_id, records, directory="sessions/2000/01/01"):
        path = self.home / directory / f"rollout-2000-01-01T00-00-00-{thread_id}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        return path

    def notification(self, thread_id=ROOT_ID, event="agent-turn-complete"):
        return json.dumps({"type": event, "thread-id": thread_id})

    def test_top_level_completion_is_accepted(self):
        for source in ("cli", "vscode", "exec"):
            with self.subTest(source=source):
                self.write_rollout(self.ROOT_ID, [self.metadata(self.ROOT_ID, source)])
                self.assertTrue(should_notify(self.notification(), self.home))

    def test_subagent_with_inherited_parent_metadata_is_rejected(self):
        self.write_rollout(self.CHILD_ID, [
            self.metadata(self.CHILD_ID, {"subagent": {"thread_spawn": {
                "parent_thread_id": self.ROOT_ID, "depth": 1,
            }}}),
            self.metadata(self.ROOT_ID, "cli"),
        ])
        self.assertFalse(should_notify(self.notification(self.CHILD_ID), self.home))

    def test_non_completion_events_are_rejected(self):
        self.write_rollout(self.ROOT_ID, [self.metadata(self.ROOT_ID, "cli")])
        for event in ("approval-requested", "task_started", "agent_message", ""):
            with self.subTest(event=event):
                self.assertFalse(should_notify(self.notification(event=event), self.home))

    def test_malformed_notifications_are_rejected(self):
        for raw in ("", "{", "[]", "null", "42", "{}", self.notification("../../test")):
            with self.subTest(raw=raw):
                self.assertFalse(should_notify(raw, self.home))

    def test_missing_session_is_rejected(self):
        self.assertFalse(should_notify(self.notification(), self.home))

    def test_unknown_or_subagent_source_is_rejected(self):
        for source in (None, "unknown", "subagent", {}, []):
            with self.subTest(source=source):
                self.write_rollout(self.ROOT_ID, [self.metadata(self.ROOT_ID, source)])
                self.assertFalse(should_notify(self.notification(), self.home))

    def test_mismatched_session_id_is_rejected(self):
        self.write_rollout(self.ROOT_ID, [self.metadata(self.CHILD_ID, "cli")])
        self.assertFalse(should_notify(self.notification(), self.home))

    def test_corrupt_metadata_is_rejected(self):
        path = self.write_rollout(self.ROOT_ID, [])
        for raw in ("", "{", "[]\n", '{"type":"session_meta","payload":null}\n'):
            with self.subTest(raw=raw):
                path.write_text(raw, encoding="utf-8")
                self.assertFalse(should_notify(self.notification(), self.home))

    def test_archived_top_level_completion_is_accepted(self):
        self.write_rollout(self.ROOT_ID, [self.metadata(self.ROOT_ID, "cli")], "archived_sessions")
        self.assertTrue(should_notify(self.notification(), self.home))


if __name__ == "__main__":
    unittest.main()
