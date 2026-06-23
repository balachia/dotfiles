#!/usr/bin/env bash
# Claude Code statusLine command
# Layout: user@host | model ·effort | context meter (w/ $cost) | 5h/7d budget
# Colors are intentionally dim-friendly (ANSI, no bold) since CC dims the status line.

input=$(cat)

user=$(whoami)
host=$(hostname -s)
model=$(echo "$input" | jq -r '.model.display_name // empty')
effort=$(echo "$input" | jq -r '.effort.level // empty')
ctx_used=$(echo "$input" | jq -r '.context_window.total_input_tokens // empty')
ctx_size=$(echo "$input" | jq -r '.context_window.context_window_size // empty')
cost=$(echo "$input" | jq -r '.cost.total_cost_usd // empty')
rl5_pct=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
rl5_reset=$(echo "$input" | jq -r '.rate_limits.five_hour.resets_at // empty')
rl7_pct=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty')
rl7_reset=$(echo "$input" | jq -r '.rate_limits.seven_day.resets_at // empty')

# ANSI colors (work well in dimmed terminal status lines)
GREEN='\033[32m'
CYAN='\033[36m'
YELLOW='\033[33m'
RESET='\033[0m'

# Context meter: a fixed-width field whose background fills left->right in proportion
# to window occupancy. The label "<pct>% <used>/<size>  $<cost>" is written on top.
# Monochrome + theme-aware (uses ANSI palette indices, so it follows the terminal theme):
#   used cells  = palette 7 bg / palette 0 fg  (inverted)
#   empty cells = palette 0 bg / palette 7 fg
ctx_seg=""
if [ -n "$ctx_used" ] && [ -n "$ctx_size" ] && [ "$ctx_size" -gt 0 ]; then
    Wt=24                                    # target minimum field width
    pct=$(awk "BEGIN{printf \"%.0f\", $ctx_used*100/$ctx_size}")
    hr_used=$(awk "BEGIN{u=$ctx_used;if(u>=1000000)printf\"%.1fM\",u/1000000;else if(u>=1000)printf\"%dk\",u/1000;else printf\"%d\",u}")
    hr_size=$(awk "BEGIN{s=$ctx_size;if(s>=1000000)printf\"%dM\",s/1000000;else if(s>=1000)printf\"%dk\",s/1000;else printf\"%d\",s}")
    # reserve fixed columns so nothing shifts as values grow: pct in 3, used in 4
    left_fixed=$(printf '%3s%% %4s/%s' "$pct" "$hr_used" "$hr_size")
    tail=""
    if [ -n "$cost" ]; then
        cost_fmt=$(awk "BEGIN{printf \"%.2f\", $cost}")
        tail="\$${cost_fmt} "          # trailing space keeps the cost one cell off the right edge
    fi
    # right-align the cost tail: pad the gap between the left cluster and it
    gap=$(( Wt - ${#left_fixed} - ${#tail} ))
    [ "$gap" -lt 1 ] && gap=1
    spaces=$(printf '%*s' "$gap" '')
    label="${left_fixed}${spaces}${tail}"
    W=${#label}
    filled=$(awk "BEGIN{f=int($W*$ctx_used/$ctx_size+0.5);if(f>$W)f=$W;if(f<0)f=0;print f}")
    left="${label:0:$filled}"
    right="${label:$filled}"
    ctx_seg=$(printf '\033[48;5;7;38;5;0m%s\033[48;5;0;38;5;7m%s\033[0m' "$left" "$right")
fi

# Rate-limit segment (terse): "h:mm XX%, Nd XX%" — 5h reset countdown + used %, then
# days-to-7d-reset + used %. resets_at are unix epoch seconds; recomputed each render.
now=$(date +%s)
rl5=""; rl7=""
if [ -n "$rl5_reset" ]; then
    r=$(( rl5_reset - now )); [ "$r" -lt 0 ] && r=0
    rl5=$(printf '%d:%02d' "$(( r / 3600 ))" "$(( (r % 3600) / 60 ))")
fi
[ -n "$rl5_pct" ] && rl5=$(printf '%s %.0f%%' "$rl5" "$rl5_pct")
if [ -n "$rl7_reset" ]; then
    r=$(( rl7_reset - now )); [ "$r" -lt 0 ] && r=0
    rl7=$(printf '%dd' "$(( r / 86400 ))")
fi
[ -n "$rl7_pct" ] && rl7=$(printf '%s %.0f%%' "$rl7" "$rl7_pct")
# color each window by domain: 5h → palette 11, 7d → palette 12 (theme-aware)
[ -n "$rl5" ] && rl5=$(printf '\033[38;5;11m%s\033[0m' "$rl5")
[ -n "$rl7" ] && rl7=$(printf '\033[38;5;12m%s\033[0m' "$rl7")
if [ -n "$rl5" ] && [ -n "$rl7" ]; then rl_seg="$rl5 $rl7"
else rl_seg="${rl5}${rl7}"; fi

# Build the line
printf "${GREEN}%s${RESET}@${CYAN}%s${RESET}" "$user" "$host"

if [ -n "$rl_seg" ]; then
    printf " | %s" "$rl_seg"
fi

if [ -n "$model" ]; then
    if [ -n "$effort" ]; then
        printf " | %s ${YELLOW}·%s${RESET}" "$model" "$effort"
    else
        printf " | %s" "$model"
    fi
fi

if [ -n "$ctx_seg" ]; then
    printf " | %s" "$ctx_seg"
fi
