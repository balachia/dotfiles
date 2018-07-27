#!/bin/sh

BIN=$1
shift

# Terminate already running bar instances
echo "Killing $BIN..."
killall -q $BIN

# Wait until the processes have been shut down
while pgrep -u $UID -x $BIN >/dev/null; do sleep 1; done

if [ $# -gt 0 ]; then
    for var in "$@"; do
        $BIN $var &
    done
else
    $BIN &
fi

echo "$BIN launched..."
