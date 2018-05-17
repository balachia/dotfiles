#!/bin/sh
# /bin/sh ./lemonbar.sh | lemonbar -dp -f "Inconsolata"
# while 1; do; echo "%{c} test"; sleep 1; echo "test"; sleep 1; done | lemonbar -dp | while read line; do eval "${line}"; done
# for i in 1 2 3 4 5; do; echo "test"; done | lemonbar -dp
/bin/sh "$HOME/.config/stumpwm/lemonbar.sh" | lemonbar -p -f "Inconsolata-g-12"
