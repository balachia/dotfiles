#!/usr/bin/env bash
# Compact power + thermal-throttle indicator for tmux statusline (macOS).
# Reads /tmp/macmon.json written every 2s by ~/.sysadmin/scripts/macmon-daemon.sh
# (sys_power watts + thermal_pressure 0..4 from the kernel).
#
# Output: ᵖ[ᴛ ]<watts>W
# Throttle T (when present):
#   thermal_pressure == 1 (Moderate)   → bright white on yellow bg
#   thermal_pressure >= 2 (Heavy+)     → bright white on bright red bg
# Power tier color (on the watts digits): auto-calibrated to observed peak.

reset="#[default]#[fg=colour8]"

[ -r /tmp/macmon.json ] || exit 0

read -r sys_power thermal cpu_temp gpu_temp <<< "$(/usr/bin/python3 - <<'PY' 2>/dev/null
import json
try:
    d = json.load(open("/tmp/macmon.json"))
    therm = d.get("thermal_pressure", 0) or 0
    t = d.get("temp", {}) or {}
    cpu = t.get("cpu_temp_avg", 0) or 0
    gpu = t.get("gpu_temp_avg", 0) or 0
    print(f'{int(d["sys_power"])} {int(therm)} {int(cpu)} {int(gpu)}')
except Exception:
    print("0 0 0 0")
PY
)"

# Auto-calibrating power peak.
pmax_watts_file=/tmp/sysstat_pmax_watts
pmax_watts=$(cat "$pmax_watts_file" 2>/dev/null || echo 60)
if [ "${sys_power:-0}" -gt "$pmax_watts" ]; then
    printf '%s\n' "$sys_power" > "$pmax_watts_file"
    pmax_watts="$sys_power"
fi

# Power color tiers as % of observed peak.
pwr_pct=$(( ${sys_power:-0} * 100 / pmax_watts ))
if   [ "$pwr_pct" -ge 90 ]; then pwr_color="#[fg=colour1,bold]"
elif [ "$pwr_pct" -ge 75 ]; then pwr_color="#[fg=colour11]"
elif [ "$pwr_pct" -ge 50 ]; then pwr_color="#[fg=colour3]"
else                             pwr_color="#[fg=colour8]"
fi

# Temperature color tiers. Anchored to macmon's *_temp_avg scale, which
# reads ~15-20°C higher than per-core sensors (btop, etc.). GPU runs hotter
# than CPU under load; same thresholds for now, revisit after log analysis.
temp_tier() {
    local t=${1:-0}
    if   [ "$t" -ge 76 ]; then echo "#[fg=colour1,bold]"
    elif [ "$t" -ge 70 ]; then echo "#[fg=colour3]"
    else                       echo "#[fg=colour8]"
    fi
}
temp_color=$(temp_tier "$cpu_temp")
gtemp_color=$(temp_tier "$gpu_temp")

# Throttle indicator from kernel thermal pressure.
throttle_glyph=""
if   [ "${thermal:-0}" -ge 2 ]; then
    throttle_glyph="#[fg=colour0,bg=colour9,bold]ᵗ${reset}${pwr_color}"
elif [ "${thermal:-0}" -ge 1 ]; then
    throttle_glyph="#[fg=colour0,bg=colour3,bold]ᵗ${reset}${pwr_color}"
fi

echo "#[fg=colour1]ᵖ${throttle_glyph}${pwr_color}${sys_power}#[fg=colour1]ʷ${temp_color}${cpu_temp}#[fg=colour1]ᶜ${gtemp_color}${gpu_temp}#[fg=colour1]ᵍ${reset}"
