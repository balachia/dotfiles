mkdir -p ~/.config/nvim
mkdir -p ~/.emacs.d

ln -sf ~/.dotfiles/.tmux.conf ~
ln -sf ~/.dotfiles/.vimrc ~
ln -sf ~/.dotfiles/.Rprofile ~
#ln -sf ~/.dotfiles/.zshrc ~ 
#ln -sf ~/.dotfiles/.zshrc.oh-my-zsh ~/.zshrc 
ln -sf ~/.dotfiles/.zshrc.prezto ~/.zshrc 
ln -sf ~/.dotfiles/.inputrc ~ 
ln -sf ~/.dotfiles/panopy.templates ~/.pandoc
ln -sf ~/.dotfiles/tex.gpp ~/.pandoc
ln -sf ~/.dotfiles/init.el ~/.emacs.d/init.el
ln -sf ~/.dotfiles/init.vim ~/.config/nvim/init.vim

