"let &t_Co=256
"let $NVIM_TUI_ENABLE_TRUE_COLOR = 1

" get os name
let os=substitute(system('uname'), '\n', '', '')

" vim-plug setup
call plug#begin('~/.vim/plugged')

" My bundles
Plug 'itchyny/lightline.vim'

" colors
Plug 'balachia/vim-ambi16'

" motion
Plug 'justinmk/vim-sneak'
Plug 'kana/vim-textobj-user'
Plug 'reedes/vim-wheel'
Plug 'reedes/vim-textobj-sentence'
Plug 'yuttie/comfortable-motion.vim'

Plug 'tpope/vim-surround'
Plug 'tpope/vim-repeat'

" programming
Plug 'airblade/vim-gitgutter'
Plug 'scrooloose/nerdcommenter'
Plug 'wellle/targets.vim'

Plug 'junegunn/fzf'
Plug 'vim-scripts/gnupg.vim'
Plug 'scrooloose/nerdtree'
Plug 'tpope/vim-fugitive'
Plug 'lambdalisue/gina.vim'
Plug 'jiangmiao/auto-pairs'
Plug 'tpope/vim-unimpaired'
"Plug 'sjl/gundo.vim'
"Plug 'junegunn/goyo.vim'
"Plug 'Pocco81/TrueZen.nvim'
"Plug 'reedes/vim-pencil'
Plug 'reedes/vim-wordy'
Plug 'reedes/vim-lexical'
"Plug 'reedes/vim-thematic'
Plug 'jpalardy/vim-slime'
Plug 'Shougo/vimproc.vim'
Plug 'Shougo/unite.vim'
"Plug 'ZoomWin'
"Plug 'troydm/zoomwintab.vim'
Plug 'tomtom/tlib_vim'
Plug 'marcweber/vim-addon-mw-utils'
"Plug 'garbas/vim-snipmate'
Plug 'kshenoy/vim-signature'
Plug 'mileszs/ack.vim'
Plug 'neomake/neomake'
Plug 'Shougo/deoplete.nvim', { 'do': ':UpdateRemotePlugins' }
Plug 'zchee/deoplete-jedi'

"LanguageClient
Plug 'autozimu/LanguageClient-neovim', {
    \ 'branch': 'next',
    \ 'do': 'bash install.sh',
    \ }
let g:LanguageClient_serverCommands = {
    \ 'r': ['R', '--slave', '-e', 'languageserver::run()'],
    \ }

"R
Plug 'jalvesaq/Nvim-R'
Plug 'mllg/vim-devtools-plugin'

" filetypes
Plug 'chrisbra/csv.vim'
Plug 'vim-pandoc/vim-pandoc'
Plug 'vim-pandoc/vim-pandoc-syntax'
"Plug 'vim-pandoc/vim-criticmarkup'
Plug 'balachia/vim-criticmarkup'
"Plug 'termoshtt/unite-bibtex'
"Plug 'balachia/unite-bibtex'
"Plug 'msprev/unite-bibtex'
Plug 'twsh/unite-bibtex'
Plug 'mattn/emmet-vim'
Plug 'chrisbra/Colorizer'
Plug 'lervag/vimtex'

" cool features
Plug 'vim-scripts/LanguageTool'
Plug 'vim-scripts/utl.vim'
Plug 'terryma/vim-multiple-cursors'
Plug 'vim-scripts/loremipsum'
Plug 'dhruvasagar/vim-table-mode'
Plug 'gerw/vim-HiLinkTrace'

" if on a personal computer (e.g. access to dropbox, internet, a screen)
if filereadable(expand('~/.personal'))
"    Plug 'kchmck/vim-coffee-script'
    Plug 'xolox/vim-misc'
    Plug 'xolox/vim-notes'
    "Plug 'suan/vim-instant-markdown'
endif

call plug#end()

"set termguicolors

" terminal colors
set background=dark
colorscheme ambi16

" BASIC SETUP TIME!
filetype indent plugin on

" keeps abandoned buffers loaded
set hidden

" smart searching
set ignorecase
set smartcase

" shows position
set ruler

" keeps status line up
set laststatus=2

" confirm on quitting
set confirm
set visualbell

" keep command window to 2 lines
set cmdheight=2

" Display line numbers on the left
set number

" need to somehow configure this to prevent magic characters from appearing
" after you hit escape
"set timeout
set notimeout
set timeoutlen=750
set ttimeoutlen=250

"NeoVim handles ESC keys as alt+key, set this to solve the problem
if has('nvim')
    set ttimeout
    set ttimeoutlen=0
endif

" Use <F11> to toggle between 'paste' and 'nopaste'
set pastetoggle=<F2>

" Indentation settings for using 2 spaces instead of tabs.
" Do not change 'tabstop' from its default value of 8 with this setup.
set shiftwidth=4
set softtabstop=4
set expandtab

" use mouse everywhere
set mouse=a

" set shell because nobody likes fish :(
set shell=/bin/sh

" Map <C-L> (redraw screen) to also turn off search highlighting until the
" next search
nnoremap <C-L> :nohl<CR><C-L>

" fzf plugin
"set rtp+=/usr/local/opt/fzf

" remap leader
let mapleader=","
let maplocalleader=mapleader

" vim sneak
nmap <Leader><Leader> <Plug>Sneak_s

" fuck folds
set nofoldenable

let g:deoplete#enable_at_startup = 1

" VIM R plugin shit
let R_source = expand('~/.vim/plugged/Nvim-R/R/tmux_split.vim')
let R_notmuxconf = 1
let R_nvimpager = "tab"
let r_syntax_folding = 1
" r plugin hijacking my buffer switch key
nmap <LocalLeader>cr <Plug>RRightComment

" R underscore rules
let R_assign = 0 
autocmd! Filetype r,rmd imap <buffer> <A--> <ESC>:call ReplaceUnderS()<CR>a

" ============================================================
" keybinds
"nmap <Leader>gs :Gstatus<cr>
"map <F8> :NERDTreeFocus<CR>

" providers
"let g:python_host_prog = '/usr/local/miniconda3/bin/python'
let g:loaded_python_provider = 1
"let g:python3_host_prog = '/usr/local/miniconda3/bin/python3'

" comfortable scroll
noremap <silent> <ScrollWheelDown> :call comfortable_motion#flick(30)<CR>
noremap <silent> <ScrollWheelUp>   :call comfortable_motion#flick(-30)<CR>

" replace shit with unite
nnoremap <Leader>; :Unite -start-insert buffer<cr>
nnoremap <Leader>? :Unite -start-insert line<cr>

" find shit with fzf
nnoremap <C-p> :FZF<cr>

" incorporate ag/ack search
let g:ackprg = 'ag --vimgrep --smart-case'

" markdown openers
nmap <Leader>vm :!open -a "Marked 2" %:r.md<CR>
nmap <Leader>vp :!open %:r.pdf<CR>
nmap <Leader>vt :e %:r.tex<CR>
nmap <Leader>vh :!open %:r.html<CR>

" markdown makers
"nnoremap <Leader>mp :w <bar> NeomakeSh panopy pdfpp %:r.md<CR>
"nnoremap <Leader>mh :w <bar> NeomakeSh panopy mjhtml %:r.md<CR>
"nnoremap <Leader>mt :w <bar> NeomakeSh panopy latexpp %:r.md<CR>
nnoremap <Leader>mp :w <bar> NeomakeSh helpan.sh pdfpp %:r.md<CR>
nnoremap <Leader>mh :w <bar> NeomakeSh helpan.sh mjhtml %:r.md<CR>
nnoremap <Leader>mt :w <bar> NeomakeSh helpan.sh latexpp %:r.md<CR>
nnoremap <Leader>mrm :w <bar> NeomakeSh Rscript -e "knitr::knit('%:r.Rmd')"<CR>
nnoremap <Leader>mrh :w <bar> NeomakeSh Rscript -e "rmarkdown::render('%:r.Rmd', output_format='html_document')"<CR>
nnoremap <Leader>mrp :w <bar> NeomakeSh Rscript -e "rmarkdown::render('%:r.Rmd', output_format='pdf_document')"<CR>

" critic markdown word count
autocmd! Filetype markdown,pandoc,rmd nmap <buffer> <Leader>wc :echom system('TEST=$(mktemp); criticmarkuphs -i ' . expand('%') . ' -o $TEST; wc -w $TEST')<CR>
autocmd! Filetype tex nmap <buffer> <Leader>wc :VimtexCountWords<cr>

" Goyo
let g:goyo_width=90
nnoremap <Leader>gy :Goyo<cr>
" lightline updates caused a Goyo regression
autocmd! User GoyoEnter call lightline#disable()
autocmd! User GoyoLeave call lightline#enable()

" vimtex!
"let g:vimtex_view_method = 'skim'

" textobj sentence time!
augroup textobj_sentence
  autocmd!
  autocmd FileType markdown,pandoc call textobj#sentence#init()
  autocmd FileType textile call textobj#sentence#init()
augroup END

" Fugitive
nnoremap <Leader>gs :Gstatus<cr>

" lightline theme
let g:lightline = {
            \ 'colorscheme': 'landscape',
            \ 'active': {
            \   'left': [ [ 'mode', 'paste' ],
            \             [ 'gina', 'readonly', 'filename', 'prose', 'modified', 'neomake' ] ],
            \   'right': [ [ 'lineinfo' ],
            \              [ 'percent' ],
            \              [ 'fileformat', 'fileencoding', 'filetype' ] ]
            \ },
            \ 'component': {
            \   'prose': '%{exists("toggle_prose")?(toggle_prose=="prose"?"PR":"CD"):""}',
            \   'gina': '%{exists("*gina#component#repo#branch")?gina#component#repo#branch():""}',
            \   'neomake': '%{!empty(neomake#GetJobs()) ? len(neomake#GetJobs()) . " NM" : ""}'
            \ },
            \ 'component_visible_condition': {
            \   'prose': '(exists("toggle_prose"))',
            \   'gina': '(exists("*gina#component#repo#branch") && ""!=gina#component#repo#branch())',
            \   'neomake': '!(empty(neomake#GetJobs()))'
            \ }
            \ }

" force gina component to load
call gina#component#repo#branch()

function! ClistLength()
    "echom 'start ' . reltimestr(reltime())
    let clist_err=0
    redir => test
    silent! clist!
    redir END
    "echom 'stop ' . reltimestr(reltime())
    return 0
    if clist_err
        let ret=0
        "return 0
    else
        let ret=len(split(test, '\n'))
        "return len(split(test, '\n'))
    endif
    echom ret
    return ret
endfunction

" pandoc shit
"let g:pandoc#biblio#bibs = [expand('~/Documents/library-clean.bib')]
let g:pandoc#biblio#bibs = [expand('~/Documents/library-zotero.bib')]
let g:pandoc#biblio#use_bibtool = 1
let g:pandoc#completion#bib#mode = 'citeproc'
let g:pandoc#formatting#mode = 'h'
let g:pandoc#formatting#textwidth = 80
" we need a way to turn off auto formatting
nmap <Leader>taf :call pandoc#formatting#ToggleAutoFormat()

" let's try to disable pandoc folding
"" HAHA I DID IT! FUCK FOLDS! THIS WAS THE SPEED ISSUE
let g:pandoc#modules#disabled = ["folding"]

" rmarkdown shit
let g:NERDCustomDelimiters = { 'rmd': { 'left': '#', 'leftAlt': '#''' } }

" unite bibtex!
"let g:unite_bibtex_bib_files=[expand('~/Documents/library-clean.bib')]
"let g:unite_bibtex_bib_files=[expand('~/Documents/library.bib')]
let g:unite_bibtex_bib_files=[expand('~/Documents/library-zotero.bib')]
let g:unite_bibtex_cache_dir=$TMPDIR
nmap <Leader>ct :Unite -start-insert bibtex<CR>
imap <C-X>c <C-o>:Unite -start-insert bibtex<CR>

" vim table mode
let g:table_mode_corner_corner="+"
let g:table_mode_header_fillchar="="

" vim-slime stuff
let g:slime_target = "tmux"
let g:slime_default_config = {"socket_name": "default", "target_pane": ".2"}
let g:slime_dont_ask_default = 1
"let g:slime_no_mappings = 1
augroup slime
    autocmd!
    autocmd Filetype python let g:slime_python_ipython = 1
    autocmd Filetype python nmap <buffer> <localleader>l <Plug>SlimeLineSend
    autocmd Filetype python nmap <buffer> <localleader>d <Plug>SlimeLineSendj
    autocmd Filetype python nmap <buffer> <localleader><enter> :call slime#send("\r")<CR>
    autocmd Filetype python nmap <buffer> <localleader>s <Plug>SlimeMotionSend
    autocmd Filetype python xmap <buffer> <localleader>s <Plug>SlimeRegionSend
    autocmd Filetype python nmap <buffer> <localleader>ss <Plug>SlimeParagraphSend
augroup END

"vimtex stuff
let g:tex_flavor = 'latex'

" slimux configuration
"map <Leader>l :SlimuxREPLSendLine<CR>
"vmap <Leader>l :SlimuxREPLSendSelection<CR>
"map <Leader>a :SlimuxShellLast<CR>
"map <Leader>k :SlimuxSendKeysLast<CR>

" kill buffer, not window
command! Bd bp | sp | bn | bd

" spellcheck
map <F5> :setlocal spell! spelllang=en_us<CR>

" symbol viz
"set listchars=eol:$,tab:>-,trail:~,extends:>,precedes:<
"map <F6> :set list!<CR>

" better fold management
autocmd InsertEnter * if !exists('w:last_fdm') | let w:last_fdm=&foldmethod | setlocal foldmethod=manual | endif
autocmd InsertLeave,WinLeave * if exists('w:last_fdm') | let &l:foldmethod=w:last_fdm | unlet w:last_fdm | endif

" window navigation
nnoremap <A-h> <C-w>h
nnoremap <A-j> <C-w>j
nnoremap <A-k> <C-w>k
nnoremap <A-l> <C-w>l
tnoremap <A-h> <C-\><C-n><C-w>h
tnoremap <A-j> <C-\><C-n><C-w>j
tnoremap <A-k> <C-\><C-n><C-w>k
tnoremap <A-l> <C-\><C-n><C-w>l

" prose mode
command! Prose inoremap <buffer> . .<C-G>u|
            \ inoremap <buffer> ! !<C-G>u|
            \ inoremap <buffer> ? ?<C-G>u|
            \ inoremap <buffer> , ,<C-G>u|
            \ let g:toggle_prose = 'prose'|
            \ augroup PROSE|
            \   autocmd InsertEnter <buffer> set fo+=a|
            \   autocmd InsertLeave <buffer> set fo-=a|
            \ augroup END
            "\ setlocal spell spelllang=sv,en
            "\     nolist nowrap tw=74 fo=t1 nonu|

command! Code silent! iunmap <buffer> .|
            \ silent! iunmap <buffer> !|
            \ silent! iunmap <buffer> ?|
            \ silent! iunmap <buffer> ,|
            \ let g:toggle_prose = 'code'|
            \ silent! autocmd! PROSE * <buffer>
            "\ setlocal nospell list nowrap
            "\     tw=74 fo=cqr1 showbreak=… nu|

nnoremap Q gwip
"autocmd FileType markdown,pandoc,rmd :Prose

function! s:lightline_update()
    if !exists('g:loaded_lightline')
        return
    endif
    try
        call lightline#init()
        call lightline#colorscheme()
        call lightline#update()
    catch
    endtry
endfunction

function! ThemeLight()
    set background=light
    "colorscheme autumnleaf
    let g:lightline.colorscheme = 'PaperColor'
    let g:lightline.colorscheme = '16color'
    call s:lightline_update()
    let g:toggles['theme'] = 'light'
endfunction

function! ThemeDark()
    set background=dark
    "colorscheme badwolf
    "let g:lightline.colorscheme = 'landscape'
    let g:lightline.colorscheme = '16color'
    call s:lightline_update()
    let g:toggles['theme'] = 'dark'
endfunction

command! Light call ThemeLight()
command! Dark call ThemeDark()

if filereadable(expand('~/.personal'))
    " notes.vim
    let g:notes_directories=['~/Dropbox/notes']
    let g:notes_suffix='.txt'
    "let g:notes_markdown_program='pandoc'
    let g:notes_markdown_program='panopynotes.sh'
    let g:notes_unicode_enabled = 0
    let g:notes_smart_quotes = 0

    " markdown preview
    let g:instant_markdown_slow = 1
    let g:instant_markdown_autostart = 0
endif

if os == 'Darwin'
    " osx copy/paste
    vmap <C-x> :!pbcopy<CR>  
    vmap <C-y> :w !pbcopy<CR><CR> 
endif

" hijack vim-r-plugin autocompletion for Rmd files
" probably the right way to do this is to fork vim-r-plugin
function! RmdOmnifunc(findstart, base)
    if RmdIsInRCode(0) == 1
        let res = rcomplete#CompleteR(a:findstart, a:base)
        return res
    else
        let res = pandoc#completion#Complete(a:findstart, a:base)
        return res
    endif
endfunction

autocmd BufNewFile,BufRead *.Rmd setlocal omnifunc=RmdOmnifunc

" multiple cursors fix
" Called once right before you start selecting multiple cursors
function! Multiple_cursors_before()
    :call deoplete#disable()
endfunction

" Called once only when the multiple selection is canceled (default <Esc>)
function! Multiple_cursors_after()
    :call deoplete#enable()
endfunction

" neomake
"autocmd! BufWritePost * Neomake
"let g:neomake_verbose = 3
let g:neomake_open_list = 2
let g:neomake_r_lintr_maker = {
    \ 'args': [],
    \ 'errorformat': 
        \ '%W%f:%l:%c: style: %m,' .
        \ '%W%f:%l:%c: warning: %m,' .
        \ '%E%f:%l:%c: error: %m,',
    \ 'exe': 'Rlinter.R'
    \ }
let g:neomake_r_enabled_makers = ['lintr']

augroup neomake_hooks
    au!
    autocmd User NeomakeJobFinished call lightline#update()
augroup END

" toggles
let g:toggles = {}
function! Toggle(toggle_var, off_val, f_off, f_on)
    if !has_key(g:toggles, a:toggle_var)
        let g:toggles[a:toggle_var] = a:off_val
    endif
    if g:toggles[a:toggle_var] ==? a:off_val
        call call(a:f_off, [])
        let g:toggles[a:toggle_var] = "!".a:off_val
    else
        call call(a:f_on, [])
        let g:toggles[a:toggle_var] = a:off_val
    endif
endfunction

function! ToggleProse()
    if !exists('g:toggle_prose')
        let g:toggle_prose = 'code'
    endif
    if g:toggle_prose == 'prose'
        :Code
    else
        :Prose
    endif
endfunction
command! ToggleProse call ToggleProse()
nnoremap <leader>top :silent! ToggleProse<CR>

nnoremap <leader>tot :call Toggle("theme", "dark", function("ThemeLight"), function("ThemeDark"))<CR>

function! WheelMode()
    nnoremap <buffer> <C-j> j
    nnoremap <buffer> <C-k> k
    nmap <buffer> j <Plug>(WheelDown)
    nmap <buffer> k <Plug>(WheelUp)
endfunction
function! NoWheelMode()
    nunmap <buffer> j
    nunmap <buffer> k
    nmap <buffer> <C-j> <Plug>(WheelDown)
    nmap <buffer> <C-k> <Plug>(WheelUp)
endfunction

nnoremap <leader>tow :call Toggle("wheel", "nowheel", function("WheelMode"), function("NoWheelMode"))<CR>

function! LinebreakModeOn()
    nnoremap <buffer> j gj
    nnoremap <buffer> k gk
endfunction
function! LinebreakModeOff()
    nunmap <buffer> j
    nunmap <buffer> k
endfunction

nnoremap <leader>tol :call Toggle("linebreak", "off", function("LinebreakModeOn"), function("LinebreakModeOff"))<CR>
    
nnoremap <leader>ton :NERDTreeToggle<CR>

" r devtools
augroup rdev
    autocmd!
    autocmd FileType r,rmd nnoremap <buffer> <leader>rdl :RLoadPackage<CR>
    autocmd FileType r,rmd nnoremap <buffer> <leader>rdc :RCheckPackage<CR>
    autocmd FileType r,rmd nnoremap <buffer> <leader>rdt :RTestPackage<CR>
    autocmd FileType r,rmd nnoremap <buffer> <leader>rdT :RTestFile<CR>
    autocmd FileType r,rmd nnoremap <buffer> <leader>rdd :RDocumentPackage<CR>
    autocmd FileType r,rmd nnoremap <buffer> <leader>rdi :RInstallPackage<CR>
    autocmd FileType r,rmd nnoremap <buffer> <leader>rdb :RBuildPackage<CR>
augroup END

nnoremap ,r :source ~/.config/nvim/init.vim<CR>

let g:lightline.colorscheme = 'ambi16'
call s:lightline_update()

nnoremap ,<space> :HLT!<cr>
