"let &t_Co=256
let $NVIM_TUI_ENABLE_TRUE_COLOR = 1

" get os name
let os=substitute(system('uname'), '\n', '', '')

" vim-plug setup
call plug#begin('~/.vim/plugged')

" My bundles
Plug 'sickill/vim-sunburst'
Plug 'The-Vim-Gardener'
Plug 'reedes/vim-colors-pencil'
Plug 'flazz/vim-colorschemes'
Plug 'w0ng/vim-hybrid'
Plug 'sjl/badwolf'
"Plug 'Vim-R-plugin'
Plug 'jalvesaq/Nvim-R'
Plug 'itchyny/lightline.vim'
"Plug 'kien/ctrlp.vim'
"Plug 'Lokaltog/vim-easymotion'
Plug 'justinmk/vim-sneak'
Plug 'tpope/vim-surround'
Plug 'tpope/vim-repeat'
"Plug 'scrooloose/syntastic'
Plug 'scrooloose/nerdcommenter'
Plug 'scrooloose/nerdtree'
Plug 'tpope/vim-fugitive'
Plug 'tpope/vim-unimpaired'
Plug 'chrisbra/csv.vim'
""Plug 'edkolev/tmuxline.vim'
Plug 'vim-pandoc/vim-pandoc'
Plug 'vim-pandoc/vim-pandoc-syntax'
"Plug 'vim-pandoc/vim-criticmarkup'
Plug 'balachia/vim-criticmarkup'
"Plug '~/Dropbox/Code/vim-criticmarkup'
""Plug 'vim-pandoc/vim-rmarkdown'
"Plug 'sjl/gundo.vim'
Plug 'junegunn/goyo.vim'
""Plug 'junegunn/limelight.vim'
Plug 'kana/vim-textobj-user'
Plug 'reedes/vim-pencil'
Plug 'reedes/vim-wheel'
Plug 'reedes/vim-wordy'
Plug 'reedes/vim-textobj-sentence'
"Plug 'reedes/vim-litecorrect'
Plug 'reedes/vim-lexical'
Plug 'reedes/vim-thematic'
Plug 'jpalardy/vim-slime'
Plug 'vim-scripts/loremipsum'
Plug 'LanguageTool'
Plug 'vim-scripts/utl.vim'
"Plug 'jceb/vim-orgmode'
"Plug 'tomvanderlee/vim-kerboscript'
Plug 'terryma/vim-multiple-cursors'
Plug 'dhruvasagar/vim-table-mode'
Plug 'gerw/vim-HiLinkTrace'
Plug 'Shougo/vimproc.vim'
Plug 'Shougo/unite.vim'
"Plug 'termoshtt/unite-bibtex'
Plug 'balachia/unite-bibtex'
"Plug 'ZoomWin'
Plug 'tomtom/tlib_vim'
Plug 'marcweber/vim-addon-mw-utils'
Plug 'garbas/vim-snipmate'
Plug 'kshenoy/vim-signature'
Plug 'takac/vim-hardtime'
Plug 'yonchu/accelerated-smooth-scroll'

" if on a personal computer (e.g. access to dropbox, internet, a screen)
if filereadable(expand('~/.personal'))
"    Plug 'kchmck/vim-coffee-script'
    Plug 'xolox/vim-misc'
    Plug 'xolox/vim-notes'
    "Plug 'suan/vim-instant-markdown'
endif

call plug#end()

"colorscheme Sunburst
"colorscheme gardener
"colorscheme ir_black
"colorscheme herald
"colorscheme jellyx
"colorscheme underwater
"colorscheme pencil
"colorscheme hybrid
colorscheme badwolf

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

" Map <C-L> (redraw screen) to also turn off search highlighting until the
" next search
nnoremap <C-L> :nohl<CR><C-L>

" remap leader
let mapleader=","
let maplocalleader=mapleader

" vim sneak
nmap <Leader><Leader> <Plug>Sneak_s


" vim-hardtime
let g:hardtime_default_on = 1
let g:hardtime_showmsg = 1
let g:hardtime_maxcount = 2

" VIM R plugin shit
if $TMUX != "" 
    let R_in_buffer = 0
    let R_applescript = 0
    let R_tmux_split = 1
endif
let R_nvimpager = "tab"
let r_syntax_folding = 1
set nofoldenable

" keybinds
" remap escape
"inoremap ;; <Esc>
inoremap jk <Esc>
"inoremap <Esc> <NOP>
" convenient CtrlP
":nmap ; :CtrlPBuffer<CR>
"nmap ? :CtrlPLine<CR>
nmap <Leader>gs :Gstatus<cr>

" replace shit with unite
"call unite#filters#matcher_default#use(['matcher_fuzzy'])
nnoremap <C-p> :Unite -start-insert file_rec/async<cr>
"nnoremap ; :Unite -quick-match buffer<cr>
nnoremap <Leader>; :Unite -start-insert buffer<cr>
nnoremap <Leader>? :Unite -start-insert line<cr>


" markdown openers
nmap <Leader>vm :!open -a "Marked 2" %<CR>
nmap <Leader>vp :!open %:r.pdf<CR>
nmap <Leader>vt :e %:r.tex<CR>
nmap <Leader>vh :!open %:r.html<CR>

" markdown makers
nmap <Leader>mp :w <bar> !panopy pdfpp %<CR>
nmap <Leader>mt :w <bar> !panopy latexpp %<CR>
nmap <Leader>mh :w <bar> !panopy html %<CR>

" rewrite for neovim job control
function! PanopyStart(args)
    echom 'start: ' . join(a:args)
    if !exists("g:panopy_temp_name")
        let g:panopy_temp_name=tempname()
    endif
    let tmp = g:panopy_temp_name
    call writefile(a:args,tmp,'w')
    let pevent = {'temp_name':tmp}
    function pevent.on_stdout(job_id,data)
        call writefile(a:data,self.temp_name,'a')
    endfunction
    function pevent.on_stderr(job_id,data)
        call writefile(a:data,self.temp_name,'a')
    endfunction
    function pevent.on_exit(job_id,data)
        let tab = tabpagenr()
        "exe 'tabnew' . self.temp_name
        "exe 'tabnext' . tab
        exe 'split' . self.temp_name
        echom 'panopy done'
    endfunction
    let job = jobstart(a:args,pevent)
endfunction

nmap <Leader>map :w <bar> call PanopyStart(['panopy','pdfpp',expand('%')])<CR>
nmap <Leader>mah :w <bar> call PanopyStart(['panopy','html',expand('%')])<CR>
nmap <Leader>mat :w <bar> call PanopyStart(['panopy','latexpp',expand('%')])<CR>

" critic markdown word count
nmap <Leader>wc :echom system('TEST=$(mktemp); criticmarkuphs ' . expand('%') . ' $TEST; wc -w $TEST')<CR>
"nmap <Leader>wc :echom system('TEST=$(mktemp); criticmarkuphs ' . expand('%') . ' $TEST; echo word count: $(cat $TEST | wc -w)')<CR>

" Goyo
let g:goyo_width=90
nnoremap <Leader>gy :Goyo<cr>
" lightline updates caused a Goyo regression
autocmd! User GoyoEnter call lightline#disable()
autocmd! User GoyoLeave call lightline#enable()

" vim-pencil time
"augroup pencil
    "autocmd!
    "autocmd FileType markdown,mkd call pencil#init()
    "autocmd FileType text         call pencil#init()
"augroup END

" textobj sentence time!
augroup textobj_sentence
  autocmd!
  autocmd FileType markdown,pandoc call textobj#sentence#init()
  autocmd FileType textile call textobj#sentence#init()
augroup END

" lightline theme
let g:lightline = {
            \ 'colorscheme': 'landscape',
            \ 'active': {
            \   'left': [ [ 'mode', 'paste' ],
            \             [ 'fugitive', 'readonly', 'filename', 'modified' ] ]
            \ },
            \ 'component': {
            \   'fugitive': '%{exists("*fugitive#head")?fugitive#head():""}'
            \ },
            \ 'component_visible_condition': {
            \   'fugitive': '(exists("*fugitive#head") && ""!=fugitive#head())'
            \ }
            \ }

" pandoc shit
let g:pandoc#biblio#bibs = [expand('~/Documents/library-clean.bib')]
let g:pandoc#biblio#use_bibtool = 1
let g:pandoc#completion#bib#mode = 'citeproc'
let g:pandoc#formatting#mode = 'h'
let g:pandoc#formatting#textwidth = 80
" we need a way to turn off auto formatting
nmap <Leader>taf :call pandoc#formatting#ToggleAutoFormat()

" unite bibtex!
let g:unite_bibtex_bib_files=[expand('~/Documents/library-clean.bib')]
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
            \ silent! autocmd! PROSE * <buffer>
            "\ setlocal nospell list nowrap
            "\     tw=74 fo=cqr1 showbreak=… nu|

nnoremap Q gwip
autocmd FileType markdown,pandoc :Prose

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

" languagetool
let g:languagetool_jar='/usr/local/Cellar/languagetool/2.8/libexec/languagetool-commandline.jar'

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

