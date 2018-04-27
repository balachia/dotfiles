#!/bin/sh

# start compton
#compton -b

# daemonize emacs
emacs --daemon

# start lemonbar
# /bin/sh "$HOME/.config/stumpwm/lemoneval.sh" &
# echo "%{c} $HOME" | lemonbar -dp &
# /bin/sh ./lemonbar.sh | lemonbar -dp &
# cat "$HOME/.config/stumpwm/lemonbar.sh" | lemonbar -dp -f "Inconsolata" &
# /bin/sh "$HOME/.config/stumpwm/lemonbar.sh" | lemonbar -dp -f "Inconsolata" &
# /bin/sh "$HOME/.config/stumpwm/lemonbar.sh" | lemonbar -dp -f "Inconsolata" &

/bin/sh "$HOME/.config/stumpwm/lemoneval.sh" &
# polybar test &

# set up wallpaper
feh --bg-fill ~/pictures/bg/bg.png

