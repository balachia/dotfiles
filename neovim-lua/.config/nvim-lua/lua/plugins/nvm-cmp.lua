return {
    "hrsh7th/nvim-cmp",
    dependencies = {
        "R-nvim/nvim-cmp",      -- r auto-completion
        "hrsh7th/cmp-buffer",   -- buffer auto-completion
        "hrsh7th/cmp-path",     -- path auto-completion
        "hrsh7th/cmp-cmdline",  -- cmdline auto-completion
    },
    config = function()
        require("cmp").setup({ sources = {{ name = "cmp_r" }}})
        require("cmp_r").setup({ })
    end,
}
