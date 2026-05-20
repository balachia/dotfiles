# PATH setup — must run before other conf.d/*.fish so tools like zoxide,
# rustup, bun can find their binaries on a cold shell (new kitty window/tab).
# conf.d/ loads before config.fish, so PATH was racy when set there.

for dir in ~/.local/bin /opt/homebrew/bin
    test -d $dir; and set PATH $dir $PATH
end
