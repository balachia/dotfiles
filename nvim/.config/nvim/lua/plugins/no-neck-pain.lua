-- no-neck-pain: center the focused buffer by padding the sides.
-- width = the target text column; pairs well with wrap+linebreak for prose.
return {
    'shortcuts/no-neck-pain.nvim',
    cmd = 'NoNeckPain',
    opts = {
        width = 100,
    },
}
