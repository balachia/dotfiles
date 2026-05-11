-- Before loading plugins, set (local) leader
vim.g.mapleader = ' '
vim.g.maplocalleader = ' '

-- Load plugin manager (currently `lazy.nvim`), and plugins
--require('manager-lazy')
require('config.lazy')

-- [[ Configuration ]]
require('options')                  -- vim options/settings
--require('colorscheme')              -- load and set up colorscheme
require('keymap')                   -- set up keymap
require('lsp')                      -- set up LSPs ???

-- [[ Plugin Configuration ]]
--require('plug-config.treesitter-config')
