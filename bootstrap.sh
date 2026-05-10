#!/usr/bin/env bash
# bootstrap.sh — toolchain requirements for these dotfiles
#
# This is a skeleton: it documents what these dotfiles expect to be installed,
# grouped by purpose. Fill in install commands per-machine — Linux pkgmgr varies,
# macOS uses brew, niche OSes (Synology DSM, Bazzite) need their own approach.
#
# Usage (eventually):
#   ./bootstrap.sh              # install everything
#   ./bootstrap.sh --minimal    # foundation only
#
# For now: read it, run the parts you need by hand.

set -euo pipefail

# ──────────────────────────────────────────────────────────────────────
# FOUNDATION — these have to exist before anything else makes sense
# ──────────────────────────────────────────────────────────────────────
# git           — version control; required to clone this repo
# stow          — symlink farm manager; how dotfiles get deployed
FOUNDATION=(git stow)

# ──────────────────────────────────────────────────────────────────────
# SHELL — fish is the daily driver; bash/zsh remain the system fallbacks
# ──────────────────────────────────────────────────────────────────────
# fish          — login shell, all interactive use
SHELL_PKGS=(fish)

# ──────────────────────────────────────────────────────────────────────
# EDITOR — neovim 0.11+ required (config uses native LSP/completion APIs)
# ──────────────────────────────────────────────────────────────────────
# neovim            — editor; needs ≥0.11 for the dotfile config to load
# tree-sitter-cli   — parser generator (NB: brew formula split — library is
#                     `tree-sitter`, binary is `tree-sitter-cli`)
EDITOR_PKGS=(neovim tree-sitter-cli)

# ──────────────────────────────────────────────────────────────────────
# MULTIPLEXER — tmux config assumes ≥3.0 (extended-keys, focus-events)
# ──────────────────────────────────────────────────────────────────────
MULTIPLEXER_PKGS=(tmux)

# ──────────────────────────────────────────────────────────────────────
# TERMINAL (Mac primary) — kitty configured; alternatives work too
# ──────────────────────────────────────────────────────────────────────
TERMINAL_PKGS=(kitty)  # cask on macOS

# ──────────────────────────────────────────────────────────────────────
# MODERN SHELL STACK — quality-of-life CLI replacements
# ──────────────────────────────────────────────────────────────────────
# eza           — ls replacement (colors, git status, tree view)
# bat           — cat with syntax highlighting + git diff markers
# fd            — find replacement (faster, gitignore-aware)
# ripgrep       — grep replacement (faster, gitignore-aware)
# zoxide        — smarter cd with frecency
# starship      — cross-shell prompt (single TOML config)
# fzf           — fuzzy finder, used by zoxide/atuin/many plugins
# git-delta     — colored side-by-side git diff pager
# atuin         — shell history → SQLite + cross-machine sync (optional)
MODERN_STACK=(eza bat fd ripgrep zoxide starship fzf git-delta)

# ──────────────────────────────────────────────────────────────────────
# DOC TOOLCHAIN (optional) — pandoc setup is in dotfiles/pandoc/
# ──────────────────────────────────────────────────────────────────────
# pandoc        — markdown → anything converter
# gpp           — generic preprocessor (used by pandoc/.pandoc/tex.gpp)
DOC_PKGS=(pandoc gpp)

# ──────────────────────────────────────────────────────────────────────
# R TOOLCHAIN (optional) — only if doing data work
# ──────────────────────────────────────────────────────────────────────
# r             — R language
# radian        — R repl with vim modes (wrapped by fish/functions/r.fish)
R_PKGS=(r radian)

# ──────────────────────────────────────────────────────────────────────
# RUNTIME / DEV (machine-by-machine; these aren't dotfiles deps but live here)
# ──────────────────────────────────────────────────────────────────────
# bun           — JS runtime / pkg manager (PATH set up in fish/conf.d/bun.fish)
# fnm           — fast node version manager (called from fish/config.fish)
RUNTIMES=(bun fnm)

# ──────────────────────────────────────────────────────────────────────
# AI / AGENT (optional, evolving)
# ──────────────────────────────────────────────────────────────────────
# ollama        — local model server (DeepSeek, Qwen, etc.)
# claude        — Claude Code CLI; install via npm/curl, see anthropic docs
# pi            — Pi coding agent; npm i -g @badlogic/pi (or via OpenClaw)
AI_PKGS=(ollama)


# ──────────────────────────────────────────────────────────────────────
# Per-OS install dispatcher (stubs — fill in when actually needed)
# ──────────────────────────────────────────────────────────────────────
install_packages() {
    local pkgs=("$@")
    case "$(uname -s)" in
        Darwin)
            # brew install "${pkgs[@]}"
            echo "[macOS] would install: ${pkgs[*]}"
            ;;
        Linux)
            if   command -v dnf    >/dev/null; then : # sudo dnf install -y "${pkgs[@]}"
            elif command -v apt    >/dev/null; then : # sudo apt install -y "${pkgs[@]}"
            elif command -v pacman >/dev/null; then : # sudo pacman -S --needed "${pkgs[@]}"
            else echo "unknown linux pkgmgr"; return 1
            fi
            echo "[linux] would install: ${pkgs[*]}"
            ;;
        *)
            echo "unsupported OS: $(uname -s)"
            return 1
            ;;
    esac
}


# ──────────────────────────────────────────────────────────────────────
# Stow execution — once packages are installed, deploy the configs
# ──────────────────────────────────────────────────────────────────────
deploy_dotfiles() {
    local repo="$(cd "$(dirname "$0")" && pwd)"
    cd "$repo"
    for d in fish kitty neovim-lua pandoc R tmux; do
        # stow "$d"
        echo "[stow] would stow: $d"
    done
}


# ──────────────────────────────────────────────────────────────────────
# Login shell — make fish the login shell (assumes fish is installed)
# ──────────────────────────────────────────────────────────────────────
set_login_shell() {
    local fish_path="$(command -v fish)"
    [ -z "$fish_path" ] && { echo "fish not installed"; return 1; }
    # grep -qF "$fish_path" /etc/shells || echo "$fish_path" | sudo tee -a /etc/shells
    # chsh -s "$fish_path"
    echo "[shell] would chsh -s $fish_path"
}


# ──────────────────────────────────────────────────────────────────────
# Niche-OS pace list — these don't follow the standard path
# ──────────────────────────────────────────────────────────────────────
# Synology DSM    — old packages, no real pkgmgr; manual builds or skip
# Bazzite         — atomic / rpm-ostree; install-needs-reboot mental model
# GL.iNet routers — opkg, very limited; skip almost everything
# corporate boxes — sudo restricted; consider linuxbrew in $HOME


# ──────────────────────────────────────────────────────────────────────
# Main — uncomment when ready to actually run
# ──────────────────────────────────────────────────────────────────────
# install_packages "${FOUNDATION[@]}" "${SHELL_PKGS[@]}" "${EDITOR_PKGS[@]}" "${MULTIPLEXER_PKGS[@]}"
# install_packages "${MODERN_STACK[@]}"
# deploy_dotfiles
# set_login_shell

echo "bootstrap.sh is currently documentation. Read sections, run as needed."
