# cooldown-log: monst3r-local passive install observer (see
# ~/.sysadmin/scripts/cooldown-log). Logs install-class invocations of
# npm/bun/uv/pip3/pipx/npx to ~/.sysadmin/logs/ to gather data for an
# eventual install-cooldown policy.
#
# Portability: guarded so the wrappers only exist on machines that
# actually have the shim installed. On every other host, this file
# loads, the test fails, and the real binaries are reached via PATH
# unchanged. Drop the wrapper for a tool by removing it from the loop.

if test -x $HOME/.sysadmin/scripts/cooldown-log
    for _cl_tool in npm bun npx pip3 pipx uv
        function $_cl_tool --inherit-variable _cl_tool --description "wrapped by cooldown-log shim"
            $HOME/.sysadmin/scripts/cooldown-log $_cl_tool $argv
        end
    end
    set -e _cl_tool
end
