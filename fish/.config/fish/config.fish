# set paths
set PATH ~/.local/bin /usr/local/bin $PATH

# color theming
if test -e ~/.theme
    theme (cat ~/.theme)
end

# source local paths
set SYSNAME (uname)
if test -e ~/.config/fish/config.fish.$SYSNAME
    source ~/.config/fish/config.fish.$SYSNAME
end

# add go to path
set -x GOPATH ~/.go
set PATH ~/.go/bin $PATH

# gpg
set -x GPG_TTY (tty)

# useful haskell stuff
#hoog() {
#    hoogle $* | head
#}

# default editor neovim! fall back to vim!
if type "nvim" > /dev/null
    set -x EDITOR 'nvim'
    set -x VISUAL 'nvim'
else
    set -x EDITOR 'vim'
    set -x VISUAL 'vim'
end

# load rvm slowish
# something about ruby?
#rvm() {
#    [[ -s "$HOME/.rvm/scripts/rvm" ]] && source "$HOME/.rvm/scripts/rvm" # Load RVM into a shell session *as a function*
#}

#[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# load nvm slow
#nvm() {
#    export NVM_DIR="/Users/avashevko/.nvm"
#    [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"  # This loads nvm
#}

#wd() {
#  . $HOME/.local/src/wd/wd.sh
#}
