-- Oil: edit the filesystem like a buffer. `-` opens the parent dir.
return {
    'stevearc/oil.nvim',
    cmd = 'Oil',
    dependencies = { 'nvim-tree/nvim-web-devicons' },
    opts = {
        view_options = {
            show_hidden = true,
        },
    },
}
