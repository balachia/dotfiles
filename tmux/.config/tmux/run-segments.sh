#!/usr/bin/env bash
# Tmux statusline segment loader.
#
# Reads ~/.config/tmux/machine (user-set per-machine, gitignored) for the
# machine name. Runs each hosts/$MACHINE/[0-9]*.sh in lex order, joined by
# two spaces. Missing machine file or missing host dir → no output.
#
# Setup on a new host:
#   echo my-machine-name > ~/.config/tmux/machine
#   mkdir -p ~/.config/tmux/hosts/my-machine-name
#   # symlink scripts in from ../../segments/, prefixed 10-, 20-, ... to set order

set -e

MACHINE_FILE="$HOME/.config/tmux/machine"
HOSTS_DIR="$HOME/.config/tmux/hosts"

if [ -r "$MACHINE_FILE" ]; then
    MACHINE=$(head -1 "$MACHINE_FILE" | tr -d '[:space:]')
fi
MACHINE="${MACHINE:-default}"

DIR="$HOSTS_DIR/$MACHINE"
[ -d "$DIR" ] || DIR="$HOSTS_DIR/default"
[ -d "$DIR" ] || exit 0

first=1
for f in "$DIR"/[0-9]*.sh; do
    [ -x "$f" ] || continue
    # Capture via $() which strips trailing newlines, so each segment's
    # internal `echo` doesn't leak \n into the status-right composition.
    out=$("$f")
    [ -n "$out" ] || continue
    if [ "$first" -eq 1 ]; then first=0; else printf '  '; fi
    printf '%s' "$out"
done
