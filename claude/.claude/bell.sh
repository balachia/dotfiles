#!/usr/bin/env bash
# Claude Code hook: emit a terminal bell so it propagates out through tmux/ssh to
# the outer terminal (kitty). Portable replacement for the macOS osascript notify
# on headless hosts. Writes to the tmux pane tty if inside tmux, else the
# controlling tty, so the BEL reaches the terminal stream rather than being
# captured as hook stdout.
tty=$(tmux display -p -t "${TMUX_PANE:-}" '#{pane_tty}' 2>/dev/null)
printf '\a' > "${tty:-/dev/tty}" 2>/dev/null || true
