return {
    'lewis6991/gitsigns.nvim',
    event = { 'BufReadPre', 'BufNewFile' },
    opts = {
        signs = {
            add          = { text = '│' },
            change       = { text = '│' },
            delete       = { text = '_' },
            topdelete    = { text = '‾' },
            changedelete = { text = '~' },
            untracked    = { text = '┆' },
        },
        on_attach = function(bufnr)
            local gs = require('gitsigns')
            local map = function(mode, l, r, desc)
                vim.keymap.set(mode, l, r, { buffer = bufnr, desc = desc })
            end
            map('n', ']c', function() gs.nav_hunk('next') end, 'next git hunk')
            map('n', '[c', function() gs.nav_hunk('prev') end, 'prev git hunk')
            map('n', '<leader>gp', gs.preview_hunk, 'preview hunk')
            map('n', '<leader>gb', function() gs.blame_line({ full = true }) end, 'blame line')
        end,
    },
}
