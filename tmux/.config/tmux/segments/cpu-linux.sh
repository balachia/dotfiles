#!/usr/bin/env bash
# CPU load (mean + worst-process %CPU) + temperature (Linux).
#
# Uses `top -bn2 -d 0.5` for delta-based instantaneous %CPU per process.
# The second iteration of top has accurate "right-now" values — same as
# what an interactive top shows — without the lifetime-average artifacts
# that make GNU ps shoot to 2700% for young multi-threaded processes.
#
# Cost: blocks ~500ms per invocation (top's -d delay between samples).
# At tmux's typical 5s refresh interval that's ~10% blocking.

source "$HOME/.config/tmux/theme.sh"

read -r mean max <<< "$(top -bn2 -d 0.5 -w 200 2>/dev/null | awk '
    /^top - / { iter++ }
    iter == 2 && /^ *PID/ {
        for (i = 1; i <= NF; i++) if ($i == "%CPU") col = i
    }
    iter == 2 && /^ *[0-9]/ && col {
        pct = $col + 0
        if (pct > 0.5) { sum += pct; n++; if (pct > max) max = pct }
    }
    END { printf "%.0f %.0f", (n ? sum/n : 0), max + 0 }
')"

mean=${mean:-0}
max=${max:-0}

if   [ "$mean" -gt 50 ]; then load_color="$TM_ALERT"
elif [ "$mean" -gt 25 ]; then load_color="$TM_WARN"
else                          load_color="$TM_BASELINE"
fi

# Temperature from thermal_zone (millidegrees C). May not be the CPU
# sensor on every machine — refine per-host if needed.
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

echo "${TM_LABEL}ᶜ${load_color}${mean}/${max}${TM_UNIT}%${temp_seg}${TM_RESET}"
