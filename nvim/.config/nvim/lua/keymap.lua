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

-- Turn off search highlight (mnemonic: / searches, leader-/ unsearches)
vim.keymap.set('n', '<leader>/', '<Cmd>nohlsearch<CR>', opts)

-- Buffer close
vim.keymap.set('n', '<leader>q', ':bp<bar>bd#<CR>', opts)

-- Oil: open parent directory as an editable buffer
vim.keymap.set('n', '-', '<Cmd>Oil<CR>', opts)
vim.keymap.set('n', '<Leader>tto', ':NvimTreeFocus<CR>', opts)
vim.keymap.set('n', '<Leader>ttc', ':NvimTreeClose<CR>', opts)

-- Center the buffer for distraction-free reading/writing (toggle)
vim.keymap.set('n', '<Leader>z', '<Cmd>NoNeckPain<CR>', opts)

-- Move by visual line when no count is given (nice with wrap + linebreak),
-- but keep numbered jumps (e.g. 5j) and relativenumber motions intact.
vim.keymap.set({ 'n', 'x' }, 'j', "v:count == 0 ? 'gj' : 'j'", { expr = true, silent = true })
vim.keymap.set({ 'n', 'x' }, 'k', "v:count == 0 ? 'gk' : 'k'", { expr = true, silent = true })
