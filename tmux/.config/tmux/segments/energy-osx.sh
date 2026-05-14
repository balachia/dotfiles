#!/usr/bin/env bash
# System power + battery + throttle (macOS).
# Power and throttle from macmon daemon; battery from pmset.
# Self-suppress: silent if neither source is available.

source "$HOME/.config/tmux/theme.sh"

# ── Power + throttle from macmon ────────────────────────────────────────
power=""
if [ -r /tmp/macmon.json ]; then
    read -r sys_power thermal <<< "$(/usr/bin/python3 - <<'PY' 2>/dev/null
import json
try:
    d = json.load(open("/tmp/macmon.json"))
    print(f'{int(d["sys_power"])} {int(d.get("thermal_pressure", 0) or 0)}')
except Exception:
    print("0 0")
PY
)"

    # Auto-calibrating power peak.
    pmax_watts_file=/tmp/sysstat_pmax_watts
    pmax_watts=$(cat "$pmax_watts_file" 2>/dev/null || echo 60)
    if [ "${sys_power:-0}" -gt "$pmax_watts" ]; then
        printf '%s\n' "$sys_power" > "$pmax_watts_file"
        pmax_watts="$sys_power"
    fi

    pwr_pct=$(( ${sys_power:-0} * 100 / pmax_watts ))
    if   [ "$pwr_pct" -ge 90 ]; then pwr_color="$TM_ALERT"
    elif [ "$pwr_pct" -ge 75 ]; then pwr_color="$TM_WARN_HI"
    elif [ "$pwr_pct" -ge 50 ]; then pwr_color="$TM_WARN"
    else                             pwr_color="$TM_BASELINE"
    fi

    throttle=""
    if   [ "${thermal:-0}" -ge 2 ]; then
        throttle="${TM_THROTTLE_ALERT}ᵗ${TM_RESET}${pwr_color}"
    elif [ "${thermal:-0}" -ge 1 ]; then
        throttle="${TM_THROTTLE_WARN}ᵗ${TM_RESET}${pwr_color}"
    fi

    power="${TM_LABEL}ᵖ${throttle}${pwr_color}${sys_power}${TM_LABEL}ʷ"
fi

# ── Battery from pmset (only if on a machine that has one) ──────────────
batt=""
if command -v pmset >/dev/null 2>&1; then
    batt=$(pmset -g batt | awk -v ac="$TM_BATTERY_AC" -v dc="$TM_BATTERY_DC" -v base="$TM_BASELINE" '
NR==1 {
    if (/AC Power/) { color = ac; arrow = "△" }
    else            { color = dc; arrow = "▽" }
}
/[0-9]+%/ {
    for (i=1; i<=NF; i++) if ($i ~ /%/) { gsub(/[;%]/, "", $i); pct = $i }
}
END {
    if (pct != "") printf "%s%s%s%s", color, arrow, base, pct
}
')
fi

# ── Compose ──────────────────────────────────────────────────────────────
if [ -n "$power" ] && [ -n "$batt" ]; then
    echo "${power} ${batt}${TM_RESET}"
elif [ -n "$power" ]; then
    echo "${power}${TM_RESET}"
elif [ -n "$batt" ]; then
    echo "${batt}${TM_RESET}"
fi
