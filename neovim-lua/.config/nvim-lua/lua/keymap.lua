-- Better window navigation
vim.keymap.set('n', '<C-h>', '<C-w>h', opts)
vim.keymap.set('n', '<C-j>', '<C-w>j', opts)
vim.keymap.set('n', '<C-k>', '<C-w>k', opts)
vim.keymap.set('n', '<C-l>', '<C-w>l', opts)

-- Better terminal navigation
vim.keymap.set('t', '<C-h>', '<cmd>wincmd h<CR>', opts)
vim.keymap.set('t', '<C-j>', '<cmd>wincmd j<CR>', opts)
vim.keymap.set('t', '<C-k>', '<cmd>wincmd k<CR>', opts)
vim.keymap.set('t', '<C-l>', '<cmd>wincmd l<CR>', opts)

-- Turn off search
--vim.keymap.set('n', )

-- Buffer close
vim.keymap.set('n', '<leader>q', ':bp<bar>bd#<CR>', opts)

-- Lazy oil opening
-- vim.keymap.set('n', '-', ':Oil --float<CR>', opts)
vim.keymap.set('n', '<Leader>tto', ':NvimTreeFocus<CR>', opts)
vim.keymap.set('n', '<Leader>ttc', ':NvimTreeClose<CR>', opts)
