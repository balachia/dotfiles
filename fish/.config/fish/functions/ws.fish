function ws --description "Workspace: bookmark dirs and start tmux sessions"
    set -l bookmarks_file ~/.config/ws/bookmarks

    # ws . — tmux in cwd
    if test (count $argv) -eq 0
        echo "Usage: ws <bookmark|.> | ws -- <path> | ws add/rm/ls"
        return 1
    end

    # Subcommands
    switch $argv[1]
        case ls
            if test -f $bookmarks_file
                cat $bookmarks_file
            else
                echo "No bookmarks."
            end
            return 0

        case add
            if test (count $argv) -lt 2
                echo "Usage: ws add <name> [dir]"
                return 1
            end
            set -l name $argv[2]
            set -l dir (pwd)
            if test (count $argv) -ge 3
                set dir (realpath $argv[3])
            end
            if not test -d $dir
                echo "ws: $dir is not a directory"
                return 1
            end
            mkdir -p (dirname $bookmarks_file)
            # Remove existing entry with same name, then append
            if test -f $bookmarks_file
                grep -v "^$name	" $bookmarks_file >$bookmarks_file.tmp
                mv $bookmarks_file.tmp $bookmarks_file
            end
            echo "$name	$dir" >>$bookmarks_file
            echo "Bookmarked $name → $dir"
            return 0

        case rm
            if test (count $argv) -lt 2
                echo "Usage: ws rm <name>"
                return 1
            end
            set -l name $argv[2]
            if test -f $bookmarks_file
                grep -v "^$name	" $bookmarks_file >$bookmarks_file.tmp
                mv $bookmarks_file.tmp $bookmarks_file
                echo "Removed $name"
            else
                echo "ws: no bookmarks file"
            end
            return 0

        case --
            # Force path mode
            if test (count $argv) -lt 2
                echo "Usage: ws -- <path>"
                return 1
            end
            set -l target (realpath $argv[2])
            if not test -d $target
                echo "ws: $argv[2] is not a directory"
                return 1
            end
            __ws_open $target
            return $status

        case .
            __ws_open (pwd)
            return $status

        case '*'
            # Try bookmark first, then path fallback
            set -l name $argv[1]
            if test -f $bookmarks_file
                set -l match (grep "^$name	" $bookmarks_file | head -1 | cut -f2)
                if test -n "$match"
                    __ws_open $match $name
                    return $status
                end
            end
            # Path fallback
            if test -d $argv[1]
                __ws_open (realpath $argv[1])
                return $status
            end
            echo "ws: '$name' is not a bookmark or directory"
            return 1
    end
end

function __ws_open --description "cd to dir and start/attach tmux session"
    set -l dir $argv[1]
    set -l bookmarks_file ~/.config/ws/bookmarks

    # Use explicit session name if provided, otherwise reverse-lookup dir in bookmarks
    set -l session_name ""
    if test (count $argv) -ge 2
        set session_name $argv[2]
    else
        if test -f $bookmarks_file
            set session_name (grep "	$dir\$" $bookmarks_file | head -1 | cut -f1)
        end
        if test -z "$session_name"
            set session_name (string trim -l -c '.' (basename $dir))
        end
    end

    cd $dir

    if test -n "$TMUX"
        return 0
    end

    tmux new-session -A -s $session_name
end
