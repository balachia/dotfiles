return {
    {
        "R-nvim/R.nvim",
        config = function() 
            local opts = {
                pipe_keymap = "<M-,>"
            }
            require("r").setup(opts)
        end,
        lazy = false
    },
    "R-nvim/cmp-r",
}
