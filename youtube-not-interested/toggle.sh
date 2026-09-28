#!/data/data/com.termux/files/usr/bin/bash
# One-button start/stop, run from the Termux:Widget home-screen shortcut.
#   toggle.sh          start if stopped, stop if running
#   toggle.sh stop     stop (used by the notification's Stop button)
DIR="$(cd "$(dirname "$0")" && pwd)"
PIDFILE="$PREFIX/tmp/yt-reset.pid"
LOG="$DIR/last-run.log"
NOTIFY_ID=yt-reset

notify() {  # silently does nothing if the Termux:API app isn't installed
    timeout 5 termux-notification --id "$NOTIFY_ID" "$@" >/dev/null 2>&1
}
toast() { timeout 5 termux-toast "$1" >/dev/null 2>&1; }

running_pid() {
    [ -f "$PIDFILE" ] || return 1
    local pid; pid=$(cat "$PIDFILE")
    kill -0 "$pid" 2>/dev/null && echo "$pid"
}

stop() {
    local pid; pid=$(running_pid) || { toast "YouTube reset isn't running"; return; }
    kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid"
    toast "Stopping YouTube reset..."
}

worker() {  # runs detached in the background
    echo $$ > "$PIDFILE"
    cleanup() {
        [ -n "$device" ] && adb -s "$device" shell svc power stayon false >/dev/null 2>&1
        termux-wake-unlock 2>/dev/null
        rm -f "$PIDFILE"
        local n; n=$(grep -c "^  MARK " "$LOG")
        local why; why=$(grep -E "^(stopped|reached|15 scrolls|couldn't|no ADB)" "$LOG" | tail -1)
        timeout 5 termux-notification-remove "$NOTIFY_ID" 2>/dev/null
        notify --title "YouTube reset finished" --content "Marked $n video(s) Not interested. ${why}"
    }
    trap cleanup EXIT
    trap 'wait; exit 143' TERM INT   # let python print its summary first

    termux-wake-lock 2>/dev/null
    cd "$DIR"
    . ./adb-connect.sh
    device=$(adb_ensure 2>>"$LOG") || exit 1
    adb -s "$device" shell input keyevent KEYCODE_WAKEUP
    adb -s "$device" shell svc power stayon true   # keep the screen on while it works
    notify --ongoing --title "YouTube reset running" --content "Tap Stop, or the widget again, to end" \
        --button1 "Stop" --button1-action "bash $DIR/toggle.sh stop"
    python -u yt_not_interested.py --serial "$device" run &
    wait $!
}

case "$1" in
    stop) stop ;;
    __worker) worker >>"$LOG" 2>&1 ;;
    *)
        if running_pid >/dev/null; then
            stop
        else
            : > "$LOG"
            setsid nohup bash "$DIR/toggle.sh" __worker >/dev/null 2>&1 &
            toast "YouTube reset started"
        fi
        ;;
esac
