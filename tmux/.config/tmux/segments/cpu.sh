#!/usr/bin/env bash
# CPU load (mean/max across active processes) + optional temperature.
# Universal: ps works on macOS + Linux. Temp source varies by platform:
#   macOS: macmon daemon's cpu_temp_avg in /tmp/macmon.json
#   Linux: /sys/class/thermal/thermal_zone0/temp (millidegrees)
# Temp silently omitted if no source available.

source "$HOME/.config/tmux/theme.sh"

read -r mean_load max_load <<< "$(ps -A -o %cpu | awk '
    NR>1 && $1>0 { s+=$1; n++; if($1>m) m=$1 }
    END { printf "%.0f %.0f", (n?s/n:0), m }
')"

if [ "${mean_load:-0}" -gt 50 ]; then load_color="$TM_ALERT"
elif [ "${mean_load:-0}" -gt 25 ]; then load_color="$TM_WARN"
else load_color="$TM_BASELINE"
fi

# Temperature (optional).
temp=""
if [ -r /tmp/macmon.json ]; then
    temp=$(/usr/bin/python3 -c '
import json, sys
try:
    print(int(json.load(open("/tmp/macmon.json"))["temp"]["cpu_temp_avg"]))
except Exception:
    sys.exit(0)
' 2>/dev/null)
elif [ -r /sys/class/thermal/thermal_zone0/temp ]; then
    temp=$(( $(cat /sys/class/thermal/thermal_zone0/temp) / 1000 ))
fi

temp_seg=""
if [ -n "$temp" ] && [ "$temp" -gt 0 ] 2>/dev/null; then
    if   [ "$temp" -ge 76 ]; then tc="$TM_ALERT"
    elif [ "$temp" -ge 70 ]; then tc="$TM_WARN"
    else tc="$TM_BASELINE"
    fi
    temp_seg=" ${tc}${temp}${TM_LABEL}ᶜ"
fi

echo "${TM_LABEL}ᶜ${load_color}${mean_load}/${max_load}${temp_seg}${TM_RESET}"
