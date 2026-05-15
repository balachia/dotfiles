#!/usr/bin/env bash
# Memory used% (macOS-specific via memory_pressure).

source "$HOME/.config/tmux/theme.sh"

mem_free_pct=$(memory_pressure 2>&1 | grep "System-wide memory free percentage" | grep -oE '[0-9]+')
mem_used_pct=$(( 100 - ${mem_free_pct:-0} ))

if   [ "${mem_free_pct:-100}" -lt 10 ]; then mc="$TM_ALERT"
elif [ "${mem_free_pct:-100}" -lt 25 ]; then mc="$TM_WARN"
else mc="$TM_BASELINE"
fi

echo "${TM_LABEL}ᵐ${mc}${mem_used_pct}${TM_UNIT}%${TM_RESET}"
