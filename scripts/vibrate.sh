#!/bin/sh
# Claude Stop hook/manual use: MS. Codex notify: MS followed by a JSON event.
MS="${1:-500}"
if [ "$#" -ge 2 ]; then
    # Subagents inherit Codex's notify setting; their completion is not the root's.
    python3 "$(dirname "$0")/codex_notify_filter.py" "$2" || exit 0
fi
PATH="/system/bin:/system/xbin:$PATH" cmd vibrator_manager synced -f oneshot "$MS" >/dev/null 2>&1
exit 0
