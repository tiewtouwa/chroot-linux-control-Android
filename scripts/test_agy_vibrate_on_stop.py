"""Exercise completion hooks without touching phone hardware."""

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import agy_vibrate_on_stop as hook


class StopHookTests(unittest.TestCase):
    def invoke(self, event, error=None):
        output = io.StringIO()
        with patch.object(hook.sys, "stdin", io.StringIO(json.dumps(event))), \
                contextlib.redirect_stdout(output), \
                patch.object(hook.subprocess, "run", side_effect=error) as run:
            self.assertEqual(hook.main(), 0)
        self.assertEqual(output.getvalue(), "{}\n")
        return run

    def test_successful_idle_completion_vibrates_once(self):
        run = self.invoke({"fullyIdle": True, "terminationReason": "model_stop"})
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0],
                         ["/system/bin/cmd", "vibrator_manager", "synced", "-f", "oneshot", "500"])
        self.assertEqual(run.call_args.kwargs["timeout"], 3)

    def test_busy_failed_and_other_stop_events_do_not_vibrate(self):
        for event in ({}, None, [],
                      {"fullyIdle": False, "terminationReason": "model_stop"},
                      {"fullyIdle": "true", "terminationReason": "model_stop"},
                      {"fullyIdle": True, "terminationReason": "tool_use"},
                      {"fullyIdle": True, "terminationReason": "cancelled"},
                      {"fullyIdle": True, "terminationReason": "model_stop", "error": "failed"}):
            with self.subTest(event=event):
                self.invoke(event).assert_not_called()

    def test_android_child_environment_is_isolated(self):
        variables = {name: "synthetic" for name in ("LD_LIBRARY_PATH", "LD_PRELOAD", "LD_AUDIT")}
        with patch.dict(os.environ, variables):
            run = self.invoke({"fullyIdle": True, "terminationReason": "model_stop"})
            for name, value in variables.items():
                self.assertNotIn(name, run.call_args.kwargs["env"])
                self.assertEqual(os.environ[name], value)

    def test_command_failures_still_allow_stop(self):
        for error in (OSError("synthetic"), subprocess.TimeoutExpired("cmd", 3)):
            with self.subTest(error=error):
                self.invoke({"fullyIdle": True, "terminationReason": "model_stop"}, error)

    def test_malformed_input_does_not_vibrate(self):
        for raw in ("", "{"):
            with self.subTest(raw=raw), patch.object(hook.sys, "stdin", io.StringIO(raw)), \
                    contextlib.redirect_stdout(io.StringIO()) as output, \
                    patch.object(hook.subprocess, "run") as run:
                self.assertEqual(hook.main(), 0)
                self.assertEqual(output.getvalue(), "{}\n")
                run.assert_not_called()

    def test_shell_entry_accepts_non_completion_without_hardware_action(self):
        script = Path(__file__).with_name("agy_vibrate_on_stop.sh")
        result = subprocess.run(["sh", str(script)], input="{}", text=True,
                                capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "{}\n")
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
