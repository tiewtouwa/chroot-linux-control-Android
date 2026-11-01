#!/usr/bin/env python3
"""任务正常完成且后台工作结束后震动；输出空 JSON，不要求 Agent 继续。"""
import json
import os
import subprocess
import sys


def main():
    try:
        event = json.load(sys.stdin)
        if (isinstance(event, dict)
                and event.get("fullyIdle") is True
                and event.get("terminationReason") == "model_stop"
                and not event.get("error")):
            environment = os.environ.copy()
            for name in ("LD_LIBRARY_PATH", "LD_PRELOAD", "LD_AUDIT"):
                environment.pop(name, None)
            subprocess.run(
                ["/system/bin/cmd", "vibrator_manager", "synced", "-f", "oneshot", "500"],
                env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=3, check=False,
            )
    except (ValueError, OSError, subprocess.TimeoutExpired):
        pass
    print("{}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
