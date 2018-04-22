"let &t_Co=256
"let $NVIM_TUI_ENABLE_TRUE_COLOR = 1

" get os name
let os=substitute(system('uname'), '\n', '', '')

" vim-plug setup
call plug#begin('~/.vim/plugged')

" My bundles
" colors
Plug 'sickill/vim-sunburst'
Plug 'vim-scripts/The-Vim-Gardener'
"Plug 'reedes/vim-colors-pencil'
Plug 'flazz/vim-colorschemes'
Plug 'w0ng/vim-hybrid'
Plug 'sjl/badwolf'

Plug 'itchyny/lightline.vim'

" motion
Plug 'justinmk/vim-sneak'
Plug 'kana/vim-textobj-user'
Plug 'reedes/vim-wheel'
Plug 'reedes/vim-textobj-sentence'
"Plug 'yonchu/accelerated-smooth-scroll'
Plug 'yuttie/comfortable-motion.vim'

Plug 'tpope/vim-surround'
Plug 'tpope/vim-repeat'

" programming
Plug 'majutsushi/tagbar'
Plug 'ludovicchabant/vim-gutentags'
Plug 'airblade/vim-gitgutter'
Plug 'scrooloose/nerdcommenter'

Plug 'scrooloose/nerdtree'
"Plug 'tpope/vim-fugitive'
Plug 'lambdalisue/gina.vim'
Plug 'tpope/vim-unimpaired'
"Plug 'sjl/gundo.vim'
Plug 'junegunn/goyo.vim'
"Plug 'reedes/vim-pencil'
Plug 'reedes/vim-wordy'
Plug 'reedes/vim-lexical'
Plug 'reedes/vim-thematic'
Plug 'jpalardy/vim-slime'
Plug 'Shougo/vimproc.vim'
Plug 'Shougo/unite.vim'
"Plug 'ZoomWin'
Plug 'troydm/zoomwintab.vim'
Plug 'tomtom/tlib_vim'
Plug 'marcweber/vim-addon-mw-utils'
Plug 'garbas/vim-snipmate'
Plug 'kshenoy/vim-signature'
Plug 'mileszs/ack.vim'
Plug 'neomake/neomake'
Plug 'Shougo/deoplete.nvim', { 'do': ':UpdateRemotePlugins' }

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

set termguicolors

"dark
"colorscheme Sunburst
"colorscheme gardener
"colorscheme ir_black
"colorscheme herald
"colorscheme jellyx
"colorscheme underwater
"colorscheme hybrid

"light
"colorscheme pencil
"colorscheme summerfruit
"colorscheme flatui
"colorscheme hemisu

"colorscheme badwolf
"colorscheme codeschool

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

" Map <C-L> (redraw screen) to also turn off search highlighting until the
" next search
nnoremap <C-L> :nohl<CR><C-L>

" fzf plugin
set rtp+=/usr/local/opt/fzf

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

" ============================================================
" keybinds
"nmap <Leader>gs :Gstatus<cr>
"map <F8> :NERDTreeFocus<CR>

" providers
"let g:python_host_prog = '/usr/local/miniconda3/bin/python'
let g:loaded_python_provider = 1
let g:python3_host_prog = '/usr/local/miniconda3/bin/python3'

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
nmap <Leader>mp :w <bar> NeomakeSh panopy pdfpp %:r.md<CR>
nmap <Leader>mh :w <bar> NeomakeSh panopy mjhtml %:r.md<CR>
nmap <Leader>mt :w <bar> NeomakeSh panopy latexpp %:r.md<CR>
nmap <Leader>mrm :w <bar> NeomakeSh Rscript -e "knitr::knit('%:r.Rmd')"<CR>
nmap <Leader>mrh :w <bar> NeomakeSh Rscript -e "rmarkdown::render('%:r.Rmd', output_format='html_document')"<CR>

" critic markdown word count
autocmd! Filetype markdown,pandoc,rmd nmap <buffer> <Leader>wc :echom system('TEST=$(mktemp); criticmarkuphs ' . expand('%') . ' $TEST; wc -w $TEST')<CR>
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

" Gina
nnoremap <Leader>gs :Gina status<cr>
nnoremap <Leader>gts :Gina status<cr>
nnoremap <Leader>gtb :Gina branch<cr>
nnoremap <Leader>gtc :Gina commit<cr>

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
let g:pandoc#biblio#bibs = [expand('~/Documents/library-clean.bib')]
let g:pandoc#biblio#use_bibtool = 1
let g:pandoc#completion#bib#mode = 'citeproc'
let g:pandoc#formatting#mode = 'h'
let g:pandoc#formatting#textwidth = 80
" we need a way to turn off auto formatting
nmap <Leader>taf :call pandoc#formatting#ToggleAutoFormat()

" let's try to disable pandoc folding
"" HAHA I DID IT! FUCK FOLDS! THIS WAS THE SPEED ISSUE
let g:pandoc#modules#disabled = ["folding"]



" unite bibtex!
"let g:unite_bibtex_bib_files=[expand('~/Documents/library-clean.bib')]
let g:unite_bibtex_bib_files=[expand('~/Documents/library.bib')]
let g:unite_bibtex_cache_dir=$TMPDIR
nmap <Leader>ct :Unite -start-insert bibtex<CR>
imap <C-X>c <C-o>:Unite -start-insert bibtex<CR>

" vim table mode
let g:table_mode_corner_corner="+"
let g:table_mode_header_fillchar="="

" vim-slime stuff
let g:slime_target = "tmux"
let g:slime_default_config = {"socket_name": "default", "target_pane": ".1"}
let g:slime_python_ipython = 1

" slimux configuration
map <Leader>l :SlimuxREPLSendLine<CR>
vmap <Leader>l :SlimuxREPLSendSelection<CR>
"map <Leader>a :SlimuxShellLast<CR>
"map <Leader>k :SlimuxSendKeysLast<CR>

" kill buffer, not window
command! Bd bp | sp | bn | bd

" spellcheck
map <F5> :setlocal spell! spelllang=en_us<CR>

" symbol viz
set listchars=eol:$,tab:>-,trail:~,extends:>,precedes:<
map <F6> :set list!<CR>

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
autocmd FileType markdown,pandoc,rmd :Prose

" light/dark colorschemes
"function! s:lightline_update()
    "if !exists('g:loaded_lightline')
        "return
    "endif
    "try
        "if g:colors_name =~# 'wombat\|solarized\|landscape\|jellybeans\|Tomorrow'
            "let g:lightline.colorscheme = substitute(substitute(g:colors_name, '-', '_', 'g'), '256.*', '', '') .
                        "\ (g:colors_name ==# 'solarized' ? '_' . &background : '')
            "call lightline#init()
            "call lightline#colorscheme()
            "call lightline#update()
        "endif
    "catch
    "endtry
"endfunction

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
    colorscheme autumnleaf
    let g:lightline.colorscheme = 'PaperColor'
    call s:lightline_update()
endfunction

function! ThemeDark()
    set background=dark
    colorscheme badwolf
    let g:lightline.colorscheme = 'landscape'
    call s:lightline_update()
endfunction

command! Light call ThemeLight()
command! Dark call ThemeDark()

"command! Light set background=light |
"    \ colorscheme autumnleaf |
"    \ let g:lightline.colorscheme = 'PaperColor' |
"    \ let g:toggle_theme = 'light' |
"    \ call s:lightline_update()
"command! Dark set background=dark |
"    \ colorscheme badwolf |
"    \ let g:lightline.colorscheme = 'landscape' |
"    \ let g:toggle_theme = 'dark' |
"    \ call s:lightline_update()

if !exists('g:toggle_theme')
    if filereadable(expand('~/.theme'))
        let user_theme=system('cat ~/.theme')
        if user_theme=~'^light.\?$'
            :Light
        else
            :Dark
        endif
    elseif strftime("%H") >= 8 && strftime("%H") < 20
        :Light
    else
        :Dark
    endif
endif

" fix broken markdown extension
" autocmd BufNewFile,BufRead *.md set filetype=markdown
"autocmd FileType pandoc setlocal tw=80 formatoptions+=t
"autocmd FileType rmd setlocal tw=80 formatoptions+=t

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

" languagetool
let g:languagetool_jar='/usr/local/Cellar/languagetool/2.8/libexec/languagetool-commandline.jar'

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

nnoremap <leader>ton :NERDTreeToggle<CR>


" r devtools
augroup rdev
    autocmd!
    autocmd FileType r,rmd nnoremap <buffer> <leader>rdl :RLoadPackage<CR>
    autocmd FileType r,rmd nnoremap <buffer> <leader>rdc :RCheckPackage<CR>
    autocmd FileType r,rmd nnoremap <buffer> <leader>rdt :RTestPackage<CR>
    autocmd FileType r,rmd nnoremap <buffer> <leader>rdd :RDocumentPackage<CR>
    autocmd FileType r,rmd nnoremap <buffer> <leader>rdb :RBuildPackage<CR>
    autocmd FileType r,rmd nnoremap <buffer> <leader>rdi :RInstallPackage<CR>
augroup END


" test test test test test
" test test test test test

"" critic markup hacking time!
"nnoremap <leader>ed :set operatorfunc=CMDelOperator<cr>g@
"vnoremap <leader>ed :<c-u>call CMOperator(visualmode(),'<','>','{--','--}')<cr>
"nnoremap <leader>ea :set operatorfunc=CMAddOperator<cr>g@
"vnoremap <leader>ea :<c-u>call CMOperator(visualmode(),'<','>','{++','++}')<cr>
"nnoremap <leader>eh :set operatorfunc=CMHilOperator<cr>g@
"vnoremap <leader>eh :<c-u>call CMOperator(visualmode(),'<','>','{==','==}')<cr>
"nnoremap <leader>ec :set operatorfunc=CMComOperator<cr>g@
"vnoremap <leader>ec :<c-u>call CMOperator(visualmode(),'<','>','{>>','<<}')<cr>
"nnoremap <leader>es :set operatorfunc=CMSubOperator<cr>g@
"vnoremap <leader>es :<c-u>call CMOperator(visualmode(),'<','>','{~~','~>~~}')<cr>

"function! CMDelOperator(type)
"    call CMOperator(a:type,'[',']','{--','--}')
"endfunction

"function! CMAddOperator(type)
"    call CMOperator(a:type,'[',']','{++','++}')
"endfunction

"function! CMHilOperator(type)
"    call CMOperator(a:type,'[',']','{==','==}')
"endfunction

"function! CMComOperator(type)
"    call CMOperator(a:type,'[',']','{>>','<<}')
"endfunction

"function! CMSubOperator(type)
"    call CMOperator(a:type,'[',']','{~~','~>~~}')
"endfunction

"function! CMOperator(type, m0, m1, t0, t1)
"    let pastem=&paste
"    set paste

"    if a:type ==# 'v' || a:type == 'char'
"        silent exe "normal! `" . a:m0 . "v`" . a:m1 . "d"
"        "silent exe "normal! i" . a:t0 . "\<esc>pa" . a:t1 . "\<esc>"
"        silent exe "normal! i" . a:t0 . "\<esc>a". a:t1 . "\<esc>g`[P"
"    elseif a:type ==# 'V' || a:type == 'line'
"        silent exe "normal! `" . a:m0 . "V`" . a:m1 . "d"
"        "silent exe "normal! O" . a:t0 . "\<esc>po" . a:t1 . "\<esc>"
"        silent exe "normal! O" . a:t0 . "\<cr>" . a:t1 . "\<esc>P"
"    endif

"    let &paste=pastem
"endfunction

