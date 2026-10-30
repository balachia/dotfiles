#!/usr/bin/env bash
# zen toggle: center a pane between two spacer panes; run again to undo.
# Usage (from a tmux binding): zen.sh <window_id> <pane_id> [width]
#        zen.sh respawn <spacer_pane> <side> <center_pane> <seed>   (restyle one spacer)
#        zen.sh fit <spacer_pane>   (re-center at @zen-width after it or the window changes)
# The center width is [width], else tmux option @zen-width, else 120.
# What the spacers show is picked by tmux option @zen-style:
#   blank (default) `cat >/dev/null`, C-d closes one by hand
#   garden|coffee|matrix|sysrain|host|transit|gallery  animations from zen-spacer.py (needs python3 with curses;
#   falls back to blank)
#   random  one of those, picked once per session
#   ink  (experimental, not in random) shan shui ridges and drifting cloud curls
# or @zen-spacer, a raw command that overrides the style (e.g. `cbonsai -l`).
# Animated spacers watch both options and respawn themselves when they change,
# so `prefix : set -g @zen-style matrix` applies live (or `setw` for one
# window, `set` for one session).
# Each spacer gets ZEN_SIDE=left|right, ZEN_SEED (one random number shared by
# both, so a scene can make the same random choice on each side), and
# ZEN_CENTER=<center pane id> (so a
# custom command can `tmux capture-pane -t $ZEN_CENTER`), and is tagged with
# the pane option @zen, which is how the second press finds them.

# options are read as the pane sees them (pane > window > session > global),
# so `setw @zen-style matrix` themes just this window, `set` this session
spacer_cmd() {
  local cmd style
  cmd=$(tmux display -p -t "$1" '#{@zen-spacer}')
  style=$(tmux display -p -t "$1" '#{@zen-style}')
  if [ "$style" = random ]; then
    # one pick per session: stable across its windows and re-toggles, and a
    # new session (or a restarted server) rolls again
    local styles=(garden coffee matrix sysrain host transit gallery) key
    key=$(tmux display -p -t "$1" '#{session_id}#{session_created}' | cksum | cut -d' ' -f1)
    style=${styles[key % ${#styles[@]}]}
  fi
  if [ -z "$cmd" ] && [ -n "$style" ] && [ "$style" != blank ] \
     && python3 -c 'import curses' 2>/dev/null; then
    cmd="$(dirname "$0")/zen-spacer.py $style"
  fi
  echo "${cmd:-cat >/dev/null}"
}

if [ "$1" = respawn ]; then
  tmux respawn-pane -k -t "$2" -e ZEN_SIDE="$3" -e ZEN_CENTER="$4" -e ZEN_SEED="$5" "$(spacer_cmd "$2")"
  exit 0
fi

zen_width() {
  local w
  w=$(tmux display -p -t "$1" '#{@zen-width}')
  case $w in ''|*[!0-9]*) w=120 ;; esac
  echo "$w"
}

if [ "$1" = fit ]; then
  width=$(zen_width "$2")
  ww=$(tmux display -p -t "$2" '#{window_width}')
  pad=$(( (ww - width - 2) / 2 ))
  [ "$pad" -lt 1 ] && { tmux display-message "zen: window too narrow for $width cols"; exit 0; }
  for p in $(tmux list-panes -t "$2" -f '#{@zen}' -F '#{pane_id}'); do
    tmux resize-pane -t "$p" -x "$pad"
  done
  exit 0
fi

win=$1 pane=$2 width=${3:-$(zen_width "$2")}

spacers=$(tmux list-panes -t "$win" -f '#{@zen}' -F '#{pane_id}')
if [ -n "$spacers" ]; then
  for p in $spacers; do tmux kill-pane -t "$p"; done
  exit 0
fi

ww=$(tmux display -p -t "$win" '#{window_width}')
pad=$(( (ww - width - 2) / 2 ))   # 2 = the two border columns
if [ "$pad" -lt 1 ]; then
  tmux display-message "zen: window too narrow for $width cols"
  exit 0
fi

cmd=$(spacer_cmd "$pane")
seed=$RANDOM
for side in left right; do
  [ "$side" = left ] && before=-b || before=
  p=$(tmux split-window -hd $before -l "$pad" -t "$pane" -e ZEN_SIDE=$side -e ZEN_CENTER="$pane" -e ZEN_SEED=$seed -P -F '#{pane_id}' "$cmd")
  tmux set -p -t "$p" @zen 1
done
