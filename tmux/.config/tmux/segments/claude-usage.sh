#!/usr/bin/env bash
# Compact Claude Code usage for tmux statusline.
# Layout: ❋ <5h-time-rune><5h-budget-bar><wk-time-dots><wk-budget-bar>
#   5h time:   2-col braille; left col = hours elapsed (0-4), right col =
#              quarter of current hour (Q1..Q4 = 1..4 dots); ~15min/step
#   5h budget: vertical eighth ▁..█; fuller = more remaining
#   wk time:   1-7 dots braille = ceil(days remaining)
#   wk budget: vertical eighth; fuller = more remaining
# Self-suppress: silent if cache doesn't exist (Claude not installed/used here).

source "$HOME/.config/tmux/theme.sh"

CACHE="$HOME/.claude/cache/usage-scrape.txt"
[ -f "$CACHE" ] || exit 0

# Staleness: report >30min gap, then bail.
case "$(uname)" in
    Darwin) mod=$(stat -f %m "$CACHE" 2>/dev/null) ;;
    *)      mod=$(stat -c %Y "$CACHE" 2>/dev/null) ;;
esac
[ -n "$mod" ] || exit 0
now=$(date +%s)
if [ $(( now - mod )) -gt 1800 ]; then
    echo "${TM_WARN}❋ stale${TM_RESET}"
    exit 0
fi

session=$(grep -A1 "Current session" "$CACHE" | tail -1 | grep -oE '[0-9]+' | head -1)
weekly=$(grep -A1 "Current week" "$CACHE" | head -2 | tail -1 | grep -oE '[0-9]+' | head -1)
sess_reset=$(grep '^# session-reset:' "$CACHE" | awk '{print $3}')
week_reset=$(grep '^# week-reset:' "$CACHE" | awk '{print $3}')

# 5h time rune (2-col braille).
runes=(
    $'⢀' $'⢠' $'⢰' $'⢸'
    $'⣀' $'⣠' $'⣰' $'⣸'
    $'⣄' $'⣤' $'⣴' $'⣼'
    $'⣆' $'⣦' $'⣶' $'⣾'
    $'⣇' $'⣧' $'⣷' $'⣿'
)
time_rune="${runes[0]}"
if [ -n "$sess_reset" ] && [ "$sess_reset" -gt 0 ] 2>/dev/null; then
    left=$(( sess_reset - now ))
    if [ "$left" -le 0 ]; then
        time_rune="${runes[19]}"
    else
        elapsed=$(( 18000 - left ))
        [ "$elapsed" -lt 0 ] && elapsed=0
        mins=$(( elapsed / 60 ))
        hr=$(( mins / 60 ))
        q=$(( (mins % 60) / 15 ))
        [ "$hr" -gt 4 ] && hr=4
        [ "$q" -gt 3 ] && q=3
        time_rune="${runes[$(( hr * 4 + q ))]}"
    fi
fi

# Weekly time dots (1-7 = ceil of days left).
wk_dots_chars=("⡀" "⣀" "⣄" "⣤" "⣦" "⣶" "⣾")
wk_dots="${wk_dots_chars[0]}"
if [ -n "$week_reset" ] && [ "$week_reset" -gt 0 ] 2>/dev/null; then
    secs_left=$(( week_reset - now ))
    if [ "$secs_left" -gt 0 ]; then
        days_left=$(( (secs_left + 86399) / 86400 ))
        [ "$days_left" -lt 1 ] && days_left=1
        [ "$days_left" -gt 7 ] && days_left=7
        wk_dots="${wk_dots_chars[$(( days_left - 1 ))]}"
    fi
fi

# Budget bars (vertical eighth, fuller = more remaining).
bar_chars=("▁" "▂" "▃" "▄" "▅" "▆" "▇" "█")
budget_bar() {
    local used=${1:-0}
    local remaining=$(( 100 - used ))
    [ "$remaining" -lt 0 ] && remaining=0
    [ "$remaining" -gt 100 ] && remaining=100
    local idx=$(( remaining * 8 / 100 ))
    [ "$idx" -gt 7 ] && idx=7
    [ "$idx" -lt 0 ] && idx=0
    printf '%s' "${bar_chars[$idx]}"
}
sess_bar=$(budget_bar "$session")
wk_bar=$(budget_bar "$weekly")

# Data color: warning-tiered on the worse of session/weekly utilization.
worst=${session:-0}
[ "${weekly:-0}" -gt "$worst" ] && worst=${weekly:-0}
if [ "$worst" -gt 90 ]; then data_color="$TM_ALERT"
elif [ "$worst" -gt 75 ]; then data_color="$TM_WARN"
else data_color="$TM_BASELINE"
fi

echo "${TM_WARN}❋ ${data_color}${time_rune}${sess_bar}${wk_dots}${wk_bar}${TM_RESET}"
