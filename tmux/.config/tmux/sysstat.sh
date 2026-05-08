#!/usr/bin/env bash
# Compact CPU + memory for tmux statusline
# Output: C mean%/max% M used%
# Both colorized: default (ok), yellow (busy/pressure), red (heavy/swapping)

reset="#[default]"

# ── CPU: mean/max across active processes ───────────────────────────────
read -r cpu_mean cpu_max <<< "$(ps -A -o %cpu | awk '
    NR>1 && $1>0 { s+=$1; n++; if($1>m) m=$1 }
    END { printf "%.0f %.0f", (n?s/n:0), m }
')"

if [ "${cpu_mean:-0}" -gt 50 ]; then
    cpu_color="#[fg=colour1]"   # red
elif [ "${cpu_mean:-0}" -gt 25 ]; then
    cpu_color="#[fg=colour3]"   # yellow
else
    cpu_color=""
fi

# ── Memory: used% with pressure-based color ─────────────────────────────
mem_free_pct=$(memory_pressure 2>&1 | grep "System-wide memory free percentage" | grep -oE '[0-9]+')
mem_used_pct=$(( 100 - ${mem_free_pct:-0} ))

if [ "${mem_free_pct:-100}" -lt 10 ]; then
    mem_color="#[fg=colour1]"   # red — swapping hard
elif [ "${mem_free_pct:-100}" -lt 25 ]; then
    mem_color="#[fg=colour3]"   # yellow — pressure
else
    mem_color=""
fi

# ── Output ──────────────────────────────────────────────────────────────
echo "${cpu_color}C ${cpu_mean}%/${cpu_max}%${reset}··${mem_color}M ${mem_used_pct}%${reset}"
