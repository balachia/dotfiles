return {
    --'balachia/vim-ambi16',
    dir='~/proj/code/vim-ambi16',
    lazy = false,
    priority = 10000,
    config = function()
            vim.opt.background = "dark"
            vim.cmd([[ colorscheme ambi16 ]])
    end,
}
