return {
    {
        "R-nvim/R.nvim",
        config = function() 
            local opts = {
                hook = {
                    on_filetype = function()
                        vim.api.nvim_buf_set_keymap(0, "i", "<M-,>", "<Plug>RInsertPipe", {})
                        -- vim.api.nvim_buf_set_keymap(0, "n", "<LocalLeader>rdo", "<Cmd> lua require('r.roxygen').insert_roxygen(vim.api.nvim_get_current_buf())<CR>", {})
                        vim.api.nvim_buf_set_keymap(0, "n", "<LocalLeader>rdo", ":Roxygenize<CR>", {})
                        vim.api.nvim_buf_set_keymap(0, "n", "<LocalLeader>rdl", "<Cmd>lua require('r.send').cmd('devtools::load_all()')<CR>", {})
                        vim.api.nvim_buf_set_keymap(0, "n", "<LocalLeader>rdd", "<Cmd>lua require('r.send').cmd('devtools::document()')<CR>", {})
                        vim.api.nvim_buf_set_keymap(0, "n", "<LocalLeader>rdt", "<Cmd>lua require('r.send').cmd('devtools::test()')<CR>", {})
                        vim.api.nvim_buf_set_keymap(0, "n", "<LocalLeader>rdc", "<Cmd>lua require('r.send').cmd('devtools::check()')<CR>", {})
                        vim.api.nvim_buf_set_keymap(0, "n", "<LocalLeader>rdi", "<Cmd>lua require('r.send').cmd('devtools::install()')<CR>", {})
                    end
                },
                view_df = {
                    open_app = "terminal:vd"
                },
                -- R_app = "PROMPT_TOOLKIT_COLOR_DEPTH=DEPTH_4_BIT radian",
            }
            require("r").setup(opts)
        end,
        lazy = false
    },
    "R-nvim/cmp-r",
}
