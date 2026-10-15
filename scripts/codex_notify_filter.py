#!/usr/bin/env python3
"""Accept completion notifications only from a known top-level Codex session."""

import json
import os
from pathlib import Path
import sys
from uuid import UUID


def should_notify(raw_notification: str, codex_home: Path) -> bool:
    try:
        notification = json.loads(raw_notification)
    except ValueError:
        return False
    if not isinstance(notification, dict):
        return False
    if notification.get("type") != "agent-turn-complete":
        return False
    thread_id = notification.get("thread-id")
    if not isinstance(thread_id, str):
        return False
    try:
        if str(UUID(thread_id)) != thread_id:
            return False
    except ValueError:
        return False

    for directory in ("sessions", "archived_sessions"):
        for rollout in (codex_home / directory).glob(f"**/rollout-*-{thread_id}.jsonl"):
            try:
                with rollout.open(encoding="utf-8") as stream:
                    # Forked rollouts also contain inherited parent metadata.
                    # Only their first record identifies the notifying session.
                    record = json.loads(stream.readline())
            except (OSError, ValueError):
                continue
            if not isinstance(record, dict) or record.get("type") != "session_meta":
                continue
            metadata = record.get("payload")
            if not isinstance(metadata, dict) or metadata.get("id") != thread_id:
                continue
            source = metadata.get("source")
            return isinstance(source, str) and source in ("cli", "vscode", "exec")

    # Missing or unfamiliar metadata must not turn into an early completion alert.
    return False


if __name__ == "__main__":
    codex_directory = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    accepted = len(sys.argv) == 2 and should_notify(sys.argv[1], codex_directory)
    sys.exit(0 if accepted else 1)
