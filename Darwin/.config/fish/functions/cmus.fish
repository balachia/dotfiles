function cmus
    tmux new-session -A -D -s cmus reattach-to-user-namespace -l cmus
end
