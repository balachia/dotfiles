#!/usr/bin/env bash
# zen toggle: center a pane between two blank spacer panes; run again to undo.
# Usage (from a tmux binding): zen.sh <window_id> <pane_id> [width]
# Spacers run `cat >/dev/null` (C-d closes one by hand) and are tagged with the
# pane option @zen, which is how the second press finds them.
win=$1 pane=$2 width=${3:-100}

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

for side in -b ''; do
  p=$(tmux split-window -hd $side -l "$pad" -t "$pane" -P -F '#{pane_id}' 'cat >/dev/null')
  tmux set -p -t "$p" @zen 1
done
