-- tab
vim.opt.tabstop = 4                 -- number of visual spaces per TAB
vim.opt.softtabstop = 4             -- number of spacesin tab when editing
vim.opt.shiftwidth = 4              -- insert 4 spaces on a tab
vim.opt.expandtab = true            -- tabs are spaces, mainly because of python

-- ui
vim.opt.number = true               -- show absolute line number
vim.opt.relativenumber = true       -- show relative line number
vim.opt.laststatus = 2              -- keep status line up
vim.opt.confirm = true              -- warn on operations requiring confirmation
vim.opt.visualbell = true           -- use visual bell on alarms
vim.opt.mouse = 'a'                 -- use mouse in all modes
vim.opt.termguicolors = false       -- disable gui colors in terminal

-- searching
vim.opt.incsearch = true            -- search as characters are entered
vim.opt.hlsearch = true             -- highlight searches
vim.opt.ignorecase = true           -- ignore case in search by default
vim.opt.smartcase = true            -- case sensitive search if using uppercase

-- shell
vim.opt.shell = '/bin/sh'           -- set posix shell. nobody likes fish :(
