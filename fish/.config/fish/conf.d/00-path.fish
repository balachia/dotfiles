# PATH setup — must run before other conf.d/*.fish so tools like zoxide,
# rustup, bun can find their binaries on a cold shell (new kitty window/tab).
# conf.d/ loads before config.fish, so PATH was racy when set there.

# Order matters: last prepend wins. ~/.local/bin must end up ahead of
# /opt/homebrew/bin so user-built tools (e.g. ~/.local/bin/tmux, the
# PR #4912 build with kitty kbd protocol) shadow brew equivalents.
for dir in /opt/homebrew/bin ~/.local/bin
    test -d $dir; and set PATH $dir $PATH
end
