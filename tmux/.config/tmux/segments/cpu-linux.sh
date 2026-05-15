#!/usr/bin/env bash
# CPU usage % + optional temperature (Linux).
#
# Uses /proc/stat with cached-delta sampling: each invocation reads the
# accumulated CPU time counters, compares against the previous sample
# cached in /tmp, and reports % CPU over the elapsed interval. The first
# invocation after boot or cache-loss shows 0%; subsequent ones are accurate.
#
# Don't try to compute "mean/max across processes" like the macOS variant —
# GNU ps's %CPU is lifetime-averaged, not instantaneous, so it produces
# nonsense in a statusline. /proc/stat is the right source on Linux.
#
# Temperature from /sys/class/thermal/thermal_zone0/temp (millidegrees C).
# That zone may not be the CPU on every machine — refine per-host if so.

source "$HOME/.config/tmux/theme.sh"

CACHE="/tmp/cpu-linux-cache"

[ -r /proc/stat ] || exit 0

# First line of /proc/stat: "cpu user nice system idle iowait irq softirq steal guest guest_nice"
read -r _ user nice system idle iowait irq softirq steal _ _ < /proc/stat

idle_now=$(( idle + iowait ))
total_now=$(( user + nice + system + idle + iowait + irq + softirq + steal ))

if [ -r "$CACHE" ]; then
    read -r idle_prev total_prev < "$CACHE"
else
    idle_prev=$idle_now
    total_prev=$total_now
fi
echo "$idle_now $total_now" > "$CACHE"

idle_delta=$(( idle_now - idle_prev ))
total_delta=$(( total_now - total_prev ))

if [ "$total_delta" -gt 0 ]; then
    cpu_pct=$(( 100 * (total_delta - idle_delta) / total_delta ))
else
    cpu_pct=0
fi

if   [ "$cpu_pct" -gt 50 ]; then load_color="$TM_ALERT"
elif [ "$cpu_pct" -gt 25 ]; then load_color="$TM_WARN"
else                              load_color="$TM_BASELINE"
fi

# Temperature.
temp=""
if [ -r /sys/class/thermal/thermal_zone0/temp ]; then
    temp=$(( $(cat /sys/class/thermal/thermal_zone0/temp) / 1000 ))
fi

temp_seg=""
if [ -n "$temp" ] && [ "$temp" -gt 0 ] 2>/dev/null; then
    if   [ "$temp" -ge 80 ]; then tc="$TM_ALERT"
    elif [ "$temp" -ge 70 ]; then tc="$TM_WARN"
    else                          tc="$TM_BASELINE"
    fi
    temp_seg=" ${tc}${temp}${TM_UNIT}ᶜ"
fi

echo "${TM_LABEL}ᶜ${load_color}${cpu_pct}${TM_UNIT}%${temp_seg}${TM_RESET}"
