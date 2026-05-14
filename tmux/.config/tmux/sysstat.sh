#!/usr/bin/env bash
# Compact CPU + memory for tmux statusline.
# Cross-platform target: works on macOS today; memory branch needs a
# /proc/meminfo fallback to be fully portable to Linux.
# Power + thermal-throttle live in their own platform-specific script
# (sysstat-power-osx.sh on macOS) so this one stays portable.

reset="#[default]#[fg=colour8]"

# ── CPU: mean/max across active processes ───────────────────────────────
read -r cpu_mean cpu_max <<< "$(ps -A -o %cpu | awk '
    NR>1 && $1>0 { s+=$1; n++; if($1>m) m=$1 }
    END { printf "%.0f %.0f", (n?s/n:0), m }
')"

if [ "${cpu_mean:-0}" -gt 50 ]; then
    cpu_color="#[fg=colour1]"
elif [ "${cpu_mean:-0}" -gt 25 ]; then
    cpu_color="#[fg=colour3]"
else
    cpu_color="#[fg=colour8]"
fi

# ── Memory: used% with pressure-based color ─────────────────────────────
# TODO: portable to Linux via /proc/meminfo (MemAvailable / MemTotal)
mem_free_pct=$(memory_pressure 2>&1 | grep "System-wide memory free percentage" | grep -oE '[0-9]+')
mem_used_pct=$(( 100 - ${mem_free_pct:-0} ))

if [ "${mem_free_pct:-100}" -lt 10 ]; then
    mem_color="#[fg=colour1]"
elif [ "${mem_free_pct:-100}" -lt 25 ]; then
    mem_color="#[fg=colour3]"
else
    mem_color="#[fg=colour8]"
fi

echo "#[fg=colour1]ᶜ${cpu_color}${cpu_mean}%/${cpu_max}%${reset}  #[fg=colour1]ᵐ${mem_color}${mem_used_pct}%${reset}"
