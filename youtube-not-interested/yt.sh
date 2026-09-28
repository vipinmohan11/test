#!/data/data/com.termux/files/usr/bin/bash
# Run by hand from Termux:
#   ./yt.sh dump
#   ./yt.sh sync-subs
#   ./yt.sh run --dry-run
#   ./yt.sh run --max 20
cd "$(dirname "$0")"
. ./adb-connect.sh

device=$(adb_ensure) || exit 1
termux-wake-lock 2>/dev/null
python yt_not_interested.py --serial "$device" "$@"
status=$?
termux-wake-unlock 2>/dev/null
exit $status
