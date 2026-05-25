# opencode CLI — only put it on PATH if it's actually installed here.
# Quarantined out of config.fish because the opencode installer scribbled
# directly into the main config; this conf.d snippet preserves the PATH
# behavior without polluting the tracked entry point.

if test -d $HOME/.opencode/bin
    fish_add_path $HOME/.opencode/bin
end
