options(repos=c(CRAN="https://cloud.r-project.org"))

.libPaths(c('~/.local/R/site-library', .libPaths()))

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
    #library(setwidth)
    if(Sys.getenv("NVIMR_TMPDIR") != ""){
        options(nvimcom.verbose = 1) # To know nvimcom was successfully loaded
        library(nvimcom)
    }
}

if(interactive()) {
    if(!exists('.env')) {
        .env <- new.env()
    } else {
        detach(.env)
    }

    .env$reloadRprofile <- function() { source('~/.Rprofile') }

    .env$objsize <- function(x) format(object.size(x), units='auto')

    .env$darkTheme <- function(verbose=FALSE) {
        .env$colorscheme <- 'dark'
        setOutputColors256(verbose=verbose)
    }

    .env$lightTheme <- function(verbose=FALSE) {
        .env$colorscheme <- 'light'
        #setOutputColors256(normal=16, negnum=166, zero=142, number=130,
        #                   date=97, string=62, const=29,
        #                   false=161, true=35, infinite=33,
        #                   stderr=27, verbose=verbose)
        setOutputColors256(normal=16, negnum=160, zero=142, number=55,
                           date=136, string=62, const=29,
                           false=161, true=35, infinite=33,
                           stderr=27, verbose=verbose)
    }

    .env$setwidth_fun <- function(howWide=Sys.getenv("COLUMNS")) {
        cat("Set width:", howWide,'\n')
        options(width=as.integer(howWide))
    }

    if(!exists('colorscheme', env=.env)) {
        if(file.exists('~/.theme')) {
            user.theme <- readLines('~/.theme', warn=FALSE)
            switch(user.theme,
                   'light'=.env$lightTheme(),
                   'dark'=.env$darkTheme())
        } else {
            hour <- as.numeric(format(Sys.time(), '%H'))
            if(hour >= 8 && hour < 20) {
                .env$lightTheme()
            } else {
                .env$darkTheme()
            }
        }
    }

    makeActiveBinding(".sw", .env$setwidth_fun, baseenv())
    makeActiveBinding(".lt", .env$lightTheme, baseenv())
    makeActiveBinding(".dt", .env$darkTheme, baseenv())

    attach(.env)
}
