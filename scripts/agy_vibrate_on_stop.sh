#!/bin/sh
# agy Stop hook: notify only after a successful, fully idle completion.
exec python3 "$(dirname "$0")/agy_vibrate_on_stop.py"
