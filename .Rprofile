options(repos=c(CRAN="http://cran.cnr.Berkeley.edu"))

# Lines added by the Vim-R-plugin command :RpluginConfig (2014-Feb-23 13:47):
if(interactive()){
    if(nchar(Sys.getenv("DISPLAY")) > 1)
        options(editor = 'gvim -f -c "set ft=r"')
    else
        options(editor = 'vim -c "set ft=r"')
    library(colorout)
    if(Sys.getenv("TERM") != "linux" && Sys.getenv("TERM") != ""){
        # Choose the colors for R output among 256 options.
        # You should run show256Colors() and help(setOutputColors256) to
        # know how to change the colors according to your taste:
        setOutputColors256(verbose = FALSE)
    }
    library(setwidth)
    library(vimcom)
}


