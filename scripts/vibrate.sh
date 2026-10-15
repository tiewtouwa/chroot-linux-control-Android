#!/bin/sh
# Claude Stop hook/manual use: MS. Codex notify: MS followed by a JSON event.
MS="${1:-500}"
case "$MS" in
    ''|*[!0-9]*)
        printf '%s\n' "Invalid duration: $MS" >&2
        exit 1
        ;;
esac
if [ "$#" -ge 2 ]; then
    # Subagents inherit Codex's notify setting; their completion is not the root's.
    python3 "$(dirname "$0")/codex_notify_filter.py" "$2" || exit 0
fi
(
    unset LD_LIBRARY_PATH LD_PRELOAD LD_AUDIT
    PATH="/system/bin:/system/xbin:$PATH" exec cmd vibrator_manager synced -f oneshot "$MS"
) >/dev/null 2>&1
exit 0
