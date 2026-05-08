#!/usr/bin/env bash
# Compact claude usage for tmux statusline — reads from cache, no API calls
# Colorized: default (ok), yellow (>75%), red (>90%)
CACHE="$HOME/.claude/cache/usage-scrape.txt"
if [ ! -f "$CACHE" ]; then
    exit 0
fi
# Check staleness (>30 min = stale)
mod=$(stat -f %m "$CACHE" 2>/dev/null) || exit 0
now=$(date +%s)
age=$(( now - mod ))
if [ "$age" -gt 1800 ]; then
    echo "··❋ stale"
    exit 0
fi
# Parse session% and weekly% from cache
session=$(grep -A1 "Current session" "$CACHE" | tail -1 | grep -oE '[0-9]+' | head -1)
weekly=$(grep -A1 "Current week" "$CACHE" | head -2 | tail -1 | grep -oE '[0-9]+' | head -1)

# Time gauge: ▁▂▃▄▅▆▇█ — fills as 5h window elapses
gauge="/"
reset=$(grep '^# session-reset:' "$CACHE" | awk '{print $3}')
if [ -n "$reset" ] && [ "$reset" -gt 0 ] 2>/dev/null; then
    left=$(( reset - $(date +%s) ))
    if [ "$left" -le 0 ]; then
        gauge="█"
    else
        # 5h = 18000s, map elapsed to 8 levels
        elapsed=$(( 18000 - left ))
        [ "$elapsed" -lt 0 ] && elapsed=0
        idx=$(( elapsed * 8 / 18000 ))
        [ "$idx" -gt 7 ] && idx=7
        chars="▁▂▃▄▅▆▇█"
        gauge=$(echo "$chars" | cut -c$(( idx + 1 )))
    fi
fi

# Color based on whichever is worse
worst=${session:-0}
if [ "${weekly:-0}" -gt "$worst" ]; then
    worst=${weekly:-0}
fi

if [ "$worst" -gt 90 ]; then
    color="#[fg=colour1]"   # red
elif [ "$worst" -gt 75 ]; then
    color="#[fg=colour3]"   # yellow
else
    color=""
fi

echo "··${color}❋ ${session:-?}%#[fg=colour8]${gauge}#[default]${color}${weekly:-?}%#[default]"
