function nvx
    touch $argv
    chmod +x $argv
    nvim $argv
end
