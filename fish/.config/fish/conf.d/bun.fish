# bun runtime — only sets up PATH if bun is actually installed here
if test -d $HOME/.bun
    set -gx BUN_INSTALL "$HOME/.bun"
    fish_add_path $BUN_INSTALL/bin
end
