#!/usr/bin/env bash
# Memory used%. Portable across macOS (memory_pressure) and Linux (/proc/meminfo).

source "$HOME/.config/tmux/theme.sh"

if command -v memory_pressure >/dev/null 2>&1; then
    mem_free_pct=$(memory_pressure 2>&1 | grep "System-wide memory free percentage" | grep -oE '[0-9]+')
elif [ -r /proc/meminfo ]; then
    mem_free_pct=$(awk '
        /^MemTotal:/      { t = $2 }
        /^MemAvailable:/  { a = $2 }
        END { if (t > 0) printf "%d", 100 * a / t; else print "100" }
    ' /proc/meminfo)
else
    exit 0
fi

mem_used_pct=$(( 100 - ${mem_free_pct:-0} ))

if   [ "${mem_free_pct:-100}" -lt 10 ]; then mc="$TM_ALERT"
elif [ "${mem_free_pct:-100}" -lt 25 ]; then mc="$TM_WARN"
else mc="$TM_BASELINE"
fi

echo "${TM_LABEL}ᵐ${mc}${mem_used_pct}${TM_RESET}"
