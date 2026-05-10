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

-- quality of life
vim.opt.undofile = true             -- persistent undo across sessions
vim.opt.splitkeep = 'screen'        -- text stays in place when opening/closing splits
vim.opt.inccommand = 'split'        -- preview :s/foo/bar matches in a split
vim.opt.scrolloff = 8               -- keep 8 lines visible above/below cursor
vim.opt.smoothscroll = true         -- smooth scroll on wrapped lines
vim.opt.cursorline = true           -- highlight current line

-- autoread: reload buffers when files change on disk (agents, git pulls, etc.)
vim.opt.autoread = true
vim.api.nvim_create_autocmd({"FocusGained", "BufEnter", "CursorHold", "CursorHoldI"}, {
    pattern = "*",
    callback = function()
        if vim.fn.mode() ~= 'c' and vim.fn.getcmdwintype() == '' then
            vim.cmd('checktime')
        end
    end,
})
vim.api.nvim_create_autocmd("FileChangedShellPost", {
    pattern = "*",
    callback = function()
        vim.notify("File changed on disk. Buffer reloaded.", vim.log.levels.WARN)
    end,
})
