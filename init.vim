let &t_Co=256

" get os name
let os=substitute(system('uname'), '\n', '', '')

" vim-plug setup
call plug#begin('~/.vim/plugged')

" My bundles
Plug 'sickill/vim-sunburst'
"Plug 'Vim-R-plugin'
Plug 'jalvesaq/Nvim-R'
Plug 'itchyny/lightline.vim'
Plug 'kien/ctrlp.vim'
"Plug 'Lokaltog/vim-easymotion'
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
Plug 'vim-pandoc/vim-criticmarkup'
"Plug 'balachia/vim-criticmarkup'
""Plug 'vim-pandoc/vim-rmarkdown'
"Plug 'tpope/vim-markdown'
"Plug 'mattly/vim-markdown-enhancements'
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
Plug 'jpalardy/vim-slime'
Plug 'vim-scripts/loremipsum'
Plug 'LanguageTool'
Plug 'vim-scripts/utl.vim'
"Plug 'jceb/vim-orgmode'
"Plug 'tomvanderlee/vim-kerboscript'
Plug 'terryma/vim-multiple-cursors'
"Plug 'AsyncCommand'
Plug 'dhruvasagar/vim-table-mode'
Plug 'gerw/vim-HiLinkTrace'
Plug 'Shougo/unite.vim'
Plug 'Shougo/vimproc.vim'
"Plug 'termoshtt/unite-bibtex'
Plug 'balachia/unite-bibtex'

" if on a personal computer (e.g. access to dropbox, internet, a screen)
if filereadable(expand('~/.personal'))
"    Plug 'kchmck/vim-coffee-script'
"    Plug 'xolox/vim-misc'
"    Plug 'xolox/vim-notes'
"    "Plug 'suan/vim-instant-markdown'
endif

call plug#end()

colorscheme Sunburst

" Attempt to determine the type of a file based on its name and possibly its
" contents. Use this to allow intelligent auto-indenting for each filetype,
" and for plugins that are filetype specific.
filetype indent plugin on

" Enable syntax highlighting
"syntax on

set hidden

" Note that not everyone likes working this way (with the hidden option).
" Alternatives include using tabs or split windows instead of re-using the same
" window as mentioned above, and/or either of the following options:
" set confirm
" set autowriteall

" Better command-line completion
set wildmenu

" Show partial commands in the last line of the screen
set showcmd

" Highlight searches (use <C-L> to temporarily turn off highlighting; see the
" mapping of <C-L> below)
set hlsearch

" Modelines have historically been a source of security vulnerabilities. As
" such, it may be a good idea to disable them and use the securemodelines
" script, <http://www.vim.org/scripts/script.php?script_id=1876>.
" set nomodeline

" Use case insensitive search, except when using capital letters
set ignorecase
set smartcase

" Allow backspacing over autoindent, line breaks and start of insert action
set backspace=indent,eol,start

" When opening a new line and no filetype-specific indenting is enabled, keep
" the same indent as the line you're currently on. Useful for READMEs, etc.
set autoindent

" Stop certain movements from always going to the first character of a line.
" While this behaviour deviates from that of Vi, it does what most users
" coming from other editors would expect.
" set nostartofline

" Display the cursor position on the last line of the screen or in the status
" line of a window
set ruler

" Always display the status line, even if only one window is displayed
set laststatus=2

" Instead of failing a command because of unsaved changes, instead raise a
" dialogue asking if you wish to save changed files.
set confirm

" Use visual bell instead of beeping when doing something wrong
set visualbell

" And reset the terminal code for the visual bell. If visualbell is set, and
" this line is also included, vim will neither flash nor beep. If visualbell
" is unset, this does nothing.
" set t_vb=

" Enable use of the mouse for all modes
set mouse=a

" Set the command window height to 2 lines, to avoid many cases of having to
" "press <Enter> to continue"
set cmdheight=2

" Display line numbers on the left
set number

" Quickly time out on keycodes, but never time out on mappings
"set notimeout ttimeout ttimeoutlen=200

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

" Indentation settings for using hard tabs for indent. Display tabs as
" two characters wide.
"set shiftwidth=2
"set tabstop=2

" Map Y to act like D and C, i.e. to yank until EOL, rather than act as yy,
" which is the default
" map Y y$

" Map <C-L> (redraw screen) to also turn off search highlighting until the
" next search
nnoremap <C-L> :nohl<CR><C-L>

" VIM R plugin shit
let vimrplugin_assign = 0
let vimrplugin_assign_map = "<M-->"
let vimrplugin_vsplit = 1
"let R_in_buffer = 0
let R_nvimpager = "tab"
let R_vsplit = 1
let r_syntax_folding = 1
let g:vimrplugin_insert_mode_cmds = 0
set nofoldenable

" keybinds
" remap escape
"inoremap ;; <Esc>
inoremap jk <Esc>
"inoremap <Esc> <NOP>
" convenient CtrlP
:nmap ; :CtrlPBuffer<CR>
nmap ? :CtrlPLine<CR>

" markdown openers
nmap <Leader>vm :!open -a "Marked 2" %<CR>
nmap <Leader>vp :!open %:r.pdf<CR>
nmap <Leader>vh :!open %:r.html<CR>

" markdown makers
nmap <Leader>mp :w <bar> !panopy pdfpp %<CR>
nmap <Leader>mt :w <bar> !panopy latexpp %<CR>
nmap <Leader>mh :w <bar> !panopy html %<CR>

" rewrite for neovim job control
function! PanopyStart(args)
    let tmp = tempname()
    call writefile(a:args,tmp,'a')
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

" critic markdown word count
nmap <Leader>wc :echom system('TEST=$(mktemp); criticmarkuphs ' . expand('%') . ' $TEST; wc -w $TEST')<CR>
"nmap <Leader>wc :echom system('TEST=$(mktemp); criticmarkuphs ' . expand('%') . ' $TEST; echo word count: $(cat $TEST | wc -w)')<CR>

" airline theme
set encoding=utf-8
set termencoding=utf-8
let g:airline_powerline_fonts = 1

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
let g:pandoc#formatting#mode = 'hA'
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

