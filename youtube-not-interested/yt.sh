#!/data/data/com.termux/files/usr/bin/bash
# Launcher for Termux: keeps Termux awake, makes sure ADB is connected, then runs the script.
#   ./yt.sh dump
#   ./yt.sh run --dry-run
#   ./yt.sh run --max 20
# Set YT_ADB_PORT to skip the port prompt, e.g. YT_ADB_PORT=41235 ./yt.sh run
cd "$(dirname "$0")"

command -v termux-wake-lock >/dev/null && termux-wake-lock

device=$(adb devices | awk 'NR>1 && $2=="device" {print $1; exit}')
if [ -z "$device" ]; then
    port="$YT_ADB_PORT"
    if [ -z "$port" ]; then
        echo "Not connected. Open Settings > Developer options > Wireless debugging"
        read -rp "and type the port shown under 'IP address & Port': " port
    fi
    adb disconnect >/dev/null 2>&1
    adb connect "localhost:$port"
    device=$(adb devices | awk 'NR>1 && $2=="device" {print $1; exit}')
    if [ -z "$device" ]; then
        echo "Still not connected. If you rebooted or it's a new install, pair again:"
        echo "  adb pair localhost:<pairing-port>"
        exit 1
    fi
fi

python yt_not_interested.py --serial "$device" "$@"
status=$?
command -v termux-wake-unlock >/dev/null && termux-wake-unlock
exit $status
