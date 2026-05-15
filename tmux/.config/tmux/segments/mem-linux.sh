#!/usr/bin/env bash
# Memory used% (Linux via /proc/meminfo).
#
# MemAvailable (kernel >= 3.14) is the right "actually free" metric — it
# accounts for reclaimable caches the way free(1) does. Falls back to
# MemFree if MemAvailable is missing (very old kernels).

source "$HOME/.config/tmux/theme.sh"

[ -r /proc/meminfo ] || exit 0

read -r total avail <<< "$(awk '
    /^MemTotal:/      { t = $2 }
    /^MemAvailable:/  { a = $2 }
    /^MemFree:/       { if (a == "") a = $2 }
    END { printf "%d %d", t, a }
' /proc/meminfo)"

[ "${total:-0}" -gt 0 ] || exit 0

mem_free_pct=$(( 100 * avail / total ))
mem_used_pct=$(( 100 - mem_free_pct ))

if   [ "$mem_free_pct" -lt 10 ]; then mc="$TM_ALERT"
elif [ "$mem_free_pct" -lt 25 ]; then mc="$TM_WARN"
else                                  mc="$TM_BASELINE"
fi

echo "${TM_LABEL}ᵐ${mc}${mem_used_pct}${TM_UNIT}%${TM_RESET}"
