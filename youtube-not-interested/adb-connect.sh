# Sourced by yt.sh and toggle.sh. Finds a working ADB connection to this phone
# without asking for a port, and prints its serial.
#
# Order: existing connection → fixed port 5555 → mDNS → scan localhost ports.
# After connecting on a random wireless-debugging port it switches adbd to
# port 5555, so later runs connect instantly until the phone reboots.

_adb_device() {
    adb devices 2>/dev/null | awk 'NR>1 && $2=="device" {print $1; exit}'
}

_adb_try() {
    adb connect "$1" 2>/dev/null | grep -q "connected to" || return 1
    sleep 1
    [ -n "$(_adb_device)" ]
}

adb_ensure() {
    adb start-server >/dev/null 2>&1
    local dev port
    dev=$(_adb_device)
    if [ -n "$dev" ]; then echo "$dev"; return 0; fi

    if _adb_try localhost:5555; then _adb_device; return 0; fi

    echo "looking for the wireless debugging port..." >&2
    port=$(adb mdns services 2>/dev/null | awk '/_adb-tls-connect/ {print $NF}' | sed 's/.*://' | head -1)
    if [ -z "$port" ] || ! _adb_try "localhost:$port"; then
        port=""
        for p in $(nmap -p 30000-49999 --open -T5 localhost 2>/dev/null | awk -F/ '/^[0-9]+\/tcp +open/ {print $1}'); do
            if _adb_try "localhost:$p"; then port=$p; break; fi
        done
    fi
    if [ -z "$port" ]; then
        echo "no ADB connection. Turn on Settings > Developer options > Wireless debugging" >&2
        echo "(Wi-Fi must be on). If this is a fresh install, pair first: adb pair localhost:<port>" >&2
        return 1
    fi

    # Switch to a fixed port so the next run doesn't need to search.
    adb -s "localhost:$port" tcpip 5555 >/dev/null 2>&1
    sleep 3
    adb disconnect >/dev/null 2>&1
    if _adb_try localhost:5555; then _adb_device; return 0; fi
    _adb_try "localhost:$port" && _adb_device
}
