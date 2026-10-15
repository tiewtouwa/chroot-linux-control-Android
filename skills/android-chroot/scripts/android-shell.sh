#!/bin/sh
# Invoke the already-visible Android shell; never mount, elevate, or connect.
set -eu

case "${1-}" in
    -h|--help)
        printf '%s\n' 'Usage: android-shell.sh --check' \
            '       android-shell.sh -c SCRIPT [ARG0 [ARG...]]' \
            'Uses /system/bin/sh with an Android-only PATH in a child process.'
        exit 0
        ;;
esac

if [ "$#" -eq 0 ]; then
    printf '%s\n' 'Missing arguments; use --help.' >&2
    exit 2
fi
if [ ! -x /system/bin/sh ]; then
    printf '%s\n' 'Android shell unavailable at /system/bin/sh; check the execution environment and existing mounts.' >&2
    exit 127
fi

if [ "$1" = --check ]; then
    if [ "$#" -ne 1 ]; then
        printf '%s\n' '--check takes no arguments.' >&2
        exit 2
    fi
    set -- -c 'set -e; id; printf "android_release="; getprop ro.build.version.release; printf "android_sdk="; getprop ro.build.version.sdk; printf "android_abi="; getprop ro.product.cpu.abi'
elif [ "$1" != -c ] || [ "$#" -lt 2 ]; then
    printf '%s\n' 'Expected --check or -c SCRIPT; use --help.' >&2
    exit 2
fi

# Preserve Android-specific variables and the caller environment otherwise.
unset LD_LIBRARY_PATH LD_PRELOAD LD_AUDIT
PATH=/product/bin:/apex/com.android.runtime/bin:/apex/com.android.art/bin:/system_ext/bin:/system/bin:/system/xbin:/odm/bin:/vendor/bin:/vendor/xbin
export PATH
exec /system/bin/sh "$@"
