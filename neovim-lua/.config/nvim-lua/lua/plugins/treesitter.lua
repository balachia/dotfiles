return {
    {
        "nvim-treesitter/nvim-treesitter",
        branch = "main",
        build = ":TSUpdate",
        config = function()
            require("nvim-treesitter").install({
                "markdown", "markdown_inline", "r", "rnoweb",
                "yaml", "latex", "lua", "vimdoc",
            })
            vim.api.nvim_create_autocmd("FileType", {
                callback = function(ev)
                    pcall(vim.treesitter.start, ev.buf)
                end,
            })
        end,
    },
    -- textsubjects: dead, incompatible with new treesitter
    -- textobjects: config API changed, re-enable if needed
}
