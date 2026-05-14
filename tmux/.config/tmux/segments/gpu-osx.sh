#!/usr/bin/env bash
# GPU load, temperature, and GPU-only power draw (Apple Silicon via macmon).
# Self-suppress: silent if macmon daemon not running.

source "$HOME/.config/tmux/theme.sh"

[ -r /tmp/macmon.json ] || exit 0

read -r gload gtemp gwatts <<< "$(/usr/bin/python3 - <<'PY' 2>/dev/null
import json
try:
    d = json.load(open("/tmp/macmon.json"))
    g_use = d.get("gpu_usage") or [0, 0]
    t = d.get("temp", {}) or {}
    print(f'{int(g_use[1]*100)} {int(t.get("gpu_temp_avg", 0))} {int(d.get("gpu_power", 0))}')
except Exception:
    print("0 0 0")
PY
)"

if [ "${gload:-0}" -gt 50 ]; then lc="$TM_ALERT"
elif [ "${gload:-0}" -gt 25 ]; then lc="$TM_WARN"
else lc="$TM_BASELINE"
fi

if   [ "${gtemp:-0}" -ge 76 ]; then tc="$TM_ALERT"
elif [ "${gtemp:-0}" -ge 70 ]; then tc="$TM_WARN"
else tc="$TM_BASELINE"
fi

echo "${TM_LABEL}ᵍ${lc}${gload} ${tc}${gtemp}${TM_LABEL}ᶜ ${TM_BASELINE}${gwatts}${TM_LABEL}ʷ${TM_RESET}"
