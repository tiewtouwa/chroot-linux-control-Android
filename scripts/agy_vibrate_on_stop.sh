#!/bin/sh
# agy Stop hook: vibrate when the turn ends, then allow the stop.
cat >/dev/null
PATH="/system/bin:/system/xbin:${PATH}"
cmd vibrator_manager synced -f oneshot 500 >/dev/null 2>&1 || true
printf '%s\n' '{"decision":"allow"}'
exit 0
