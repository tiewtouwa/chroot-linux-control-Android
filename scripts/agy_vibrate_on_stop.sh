#!/bin/sh
# agy Stop hook: vibrate when the turn ends, then allow the stop.
cat >/dev/null
sh "$(dirname "$0")/vibrate.sh" 500 || true
printf '%s\n' '{"decision":"allow"}'
exit 0
