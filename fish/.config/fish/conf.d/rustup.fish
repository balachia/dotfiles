# rustup environment — only sources if cargo's env file exists
test -f $HOME/.cargo/env.fish; and source $HOME/.cargo/env.fish
