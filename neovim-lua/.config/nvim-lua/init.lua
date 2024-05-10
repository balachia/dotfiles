-- Before loading plugins, set (local) leader
vim.g.mapleader = ' '
vim.g.maplocalleader = ' '

-- Load plugin manager (currently `lazy.nvim`), and plugins
require('manager-lazy')

-- [[ Configuration ]]
require('options')          -- vim options/settings
require('colorscheme')      -- load and set up colorscheme
require('keymap')           -- set up keymap
