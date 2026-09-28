#!/data/data/com.termux/files/usr/bin/bash
# Run the reset once, later today, then never again.
#   ./schedule-once.sh 21:30     schedule it (24-hour time, today)
#   ./schedule-once.sh status    is one scheduled?
#   ./schedule-once.sh cancel    cancel it
#
# At that time it waits until the phone is unlocked, warns 30 seconds ahead
# (with a Cancel button), then starts the same run as the widget button.
# If the phone stays locked or unreachable until midnight, it gives up.
DIR="$(cd "$(dirname "$0")" && pwd)"
PIDFILE="$PREFIX/tmp/yt-once.pid"
INFOFILE="$PREFIX/tmp/yt-once.at"
NOTIFY_ID=yt-once
RETRY_SECS=${YT_RETRY_SECS:-300}
WARN_SECS=${YT_WARN_SECS:-30}

notify() { timeout 5 termux-notification --id "$NOTIFY_ID" "$@" >/dev/null 2>&1; }
cancel_button=(--button1 "Cancel" --button1-action "bash $DIR/schedule-once.sh cancel")

waiting_pid() {
    [ -f "$PIDFILE" ] || return 1
    local pid; pid=$(cat "$PIDFILE")
    kill -0 "$pid" 2>/dev/null && echo "$pid"
}

phone_locked() {  # $1 = adb serial
    adb -s "$1" shell dumpsys window 2>/dev/null |
        grep -Eqi '(mDreamingLockscreen|mShowingLockscreen|isKeyguardShowing|mKeyguardShowing)=true'
}

waiter() {  # $1 = start epoch, $2 = give-up epoch, $3 = HH:MM for messages
    echo $$ > "$PIDFILE"
    echo "$3" > "$INFOFILE"
    trap 'rm -f "$PIDFILE" "$INFOFILE"; termux-wake-unlock 2>/dev/null' EXIT
    termux-wake-lock 2>/dev/null   # keeps the timer running while the phone sleeps
    notify --title "YouTube reset scheduled" --content "Runs once today at $3" "${cancel_button[@]}"

    local now; now=$(date +%s)
    [ "$1" -gt "$now" ] && sleep $(( $1 - now ))

    cd "$DIR"
    . ./adb-connect.sh
    while [ "$(date +%s)" -lt "$2" ]; do
        device=$(adb_ensure 2>/dev/null)
        if [ -n "$device" ] && ! phone_locked "$device"; then
            notify --title "YouTube reset starts in ${WARN_SECS} s" \
                --content "It will take over the screen for a few minutes" "${cancel_button[@]}"
            sleep "$WARN_SECS"
            timeout 5 termux-notification-remove "$NOTIFY_ID" 2>/dev/null
            bash "$DIR/toggle.sh"
            exit 0
        fi
        notify --title "YouTube reset waiting" \
            --content "Unlock the phone (and keep Wireless debugging on) to start it" "${cancel_button[@]}"
        sleep "$RETRY_SECS"
    done
    notify --title "YouTube reset skipped today" --content "The phone stayed locked or Wireless debugging was off"
}

case "$1" in
    cancel)
        if pid=$(waiting_pid); then
            kill "$pid"
            timeout 5 termux-notification-remove "$NOTIFY_ID" 2>/dev/null
            timeout 5 termux-toast "Scheduled YouTube reset cancelled" 2>/dev/null
            echo "cancelled"
        else
            echo "nothing scheduled"
        fi
        ;;
    status)
        if waiting_pid >/dev/null; then echo "scheduled for $(cat "$INFOFILE") today"; else echo "nothing scheduled"; fi
        ;;
    __wait)
        waiter "$2" "$3" "$4" ;;
    [0-9]*:[0-9]*)
        start=$(date -d "today $1" +%s 2>/dev/null) || { echo "bad time: $1 (use 24-hour HH:MM)"; exit 1; }
        [ "$start" -gt "$(date +%s)" ] || { echo "$1 has already passed today"; exit 1; }
        end=$(date -d "tomorrow 00:00" +%s)
        if pid=$(waiting_pid); then kill "$pid"; echo "replaced the earlier schedule"; fi
        setsid nohup bash "$DIR/schedule-once.sh" __wait "$start" "$end" "$1" >/dev/null 2>&1 &
        echo "scheduled: runs once today at $1. Cancel with ./schedule-once.sh cancel"
        ;;
    *)
        sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
        exit 1
        ;;
esac
