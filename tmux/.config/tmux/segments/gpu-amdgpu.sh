#!/usr/bin/env bash
# AMD GPU stats for tmux statusline (Linux, amdgpu driver).
#
# Reads sysfs directly — no rocm-smi/amdgpu_top dependency, no root, fast.
# Auto-probes the card and its hwmon, with fallbacks for the discrete-vs-iGPU
# differences (Strix Halo has no amdgpu temp sensors and uses GTT not VRAM).
#
# Flags select which subfields to emit (default: all):
#   -u  utilization %
#   -m  memory used % (VRAM on discrete, GTT on iGPU)
#   -t  temperature °C (amdgpu edge, falls back to k10temp Tctl)
#   -p  power W (amdgpu power1_average)
# Silent (exit 0) if no amdgpu card is found.
#
# Note on -p semantics: amdgpu power1_average is card TBP on discrete cards
# (genuinely GPU power) but PPT — whole-package envelope (CPU+iGPU+IF+memctl)
# — on APUs. On APU hosts, prefer leaving -p off here and using the standalone
# power-amdgpu.sh segment, which carries no GPU-domain implication.

source "$HOME/.config/tmux/theme.sh"

# ── Argv ────────────────────────────────────────────────────────────────
show_u=0 show_m=0 show_t=0 show_p=0
if [ "$#" -eq 0 ]; then
    show_u=1; show_m=1; show_t=1; show_p=1
else
    while getopts "umtp" opt; do
        case $opt in
            u) show_u=1 ;;
            m) show_m=1 ;;
            t) show_t=1 ;;
            p) show_p=1 ;;
        esac
    done
fi

# ── Find the amdgpu card and its hwmon ──────────────────────────────────
card=""
for c in /sys/class/drm/card[0-9]*; do
    [ -e "$c/device/gpu_busy_percent" ] || continue
    # Confirm it's amdgpu (not e.g. an i915 card that also exposes gpu_busy).
    [ -d "$c/device/hwmon" ] || continue
    for h in "$c"/device/hwmon/hwmon*; do
        [ "$(cat "$h/name" 2>/dev/null)" = "amdgpu" ] && { card="$c"; card_hwmon="$h"; break 2; }
    done
done
[ -n "$card" ] || exit 0

# ── Field readers ───────────────────────────────────────────────────────

read_util() {
    cat "$card/device/gpu_busy_percent" 2>/dev/null
}

read_mem_pct() {
    # Discrete cards expose real VRAM in mem_info_vram_total. Strix Halo and
    # other iGPUs report a tiny BIOS framebuffer slice there (often <1 GiB);
    # their actual working set lives in GTT (system RAM mapped for GPU).
    local used total
    total=$(cat "$card/device/mem_info_vram_total" 2>/dev/null)
    if [ "${total:-0}" -gt $((1024 * 1024 * 1024)) ]; then
        used=$(cat "$card/device/mem_info_vram_used" 2>/dev/null)
    else
        total=$(cat "$card/device/mem_info_gtt_total" 2>/dev/null)
        used=$(cat "$card/device/mem_info_gtt_used" 2>/dev/null)
    fi
    [ "${total:-0}" -gt 0 ] || return
    echo $(( 100 * used / total ))
}

read_temp() {
    # Edge temp on the amdgpu hwmon, if present (discrete cards). Strix Halo's
    # amdgpu hwmon has no temp inputs; the closest signal is k10temp Tctl,
    # which reports the package thermal (CPU + iGPU on the same die).
    local t
    t=$(cat "$card_hwmon/temp1_input" 2>/dev/null)
    if [ -z "$t" ]; then
        for h in /sys/class/hwmon/hwmon*; do
            [ "$(cat "$h/name" 2>/dev/null)" = "k10temp" ] || continue
            t=$(cat "$h/temp1_input" 2>/dev/null)
            break
        done
    fi
    [ -n "$t" ] && echo $(( t / 1000 ))
}

read_watts() {
    local w
    w=$(cat "$card_hwmon/power1_average" 2>/dev/null)
    [ -n "$w" ] && echo $(( w / 1000000 ))
}

# ── Color helpers (shared thresholds with osx side) ─────────────────────

util_color()  { local v=${1:-0}; if [ "$v" -gt 50 ]; then echo "$TM_ALERT"; elif [ "$v" -gt 25 ]; then echo "$TM_WARN"; else echo "$TM_BASELINE"; fi; }
mem_color()   { local v=${1:-0}; if [ "$v" -gt 90 ]; then echo "$TM_ALERT"; elif [ "$v" -gt 75 ]; then echo "$TM_WARN"; else echo "$TM_BASELINE"; fi; }
temp_color()  { local v=${1:-0}; if [ "$v" -ge 80 ]; then echo "$TM_ALERT"; elif [ "$v" -ge 70 ]; then echo "$TM_WARN"; else echo "$TM_BASELINE"; fi; }
pwr_color()   { local v=${1:-0}; if [ "$v" -ge 200 ]; then echo "$TM_ALERT"; elif [ "$v" -ge 100 ]; then echo "$TM_WARN_HI"; elif [ "$v" -ge 50 ]; then echo "$TM_WARN"; else echo "$TM_BASELINE"; fi; }

# ── Compose ─────────────────────────────────────────────────────────────
out=""

if [ "$show_u" -eq 1 ]; then
    u=$(read_util)
    if [ -n "$u" ]; then
        c=$(util_color "$u")
        out="${out}${TM_LABEL}ᵍ${c}${u}${TM_UNIT}% "
    fi
fi

if [ "$show_m" -eq 1 ]; then
    m=$(read_mem_pct)
    if [ -n "$m" ]; then
        c=$(mem_color "$m")
        out="${out}${c}${m}${TM_UNIT}ᵐ "
    fi
fi

if [ "$show_t" -eq 1 ]; then
    t=$(read_temp)
    if [ -n "$t" ] && [ "$t" -gt 0 ]; then
        c=$(temp_color "$t")
        out="${out}${c}${t}${TM_UNIT}ᶜ "
    fi
fi

if [ "$show_p" -eq 1 ]; then
    w=$(read_watts)
    if [ -n "$w" ]; then
        c=$(pwr_color "$w")
        # No ᵖ prefix: inside the gpu segment, the leading ᵍ already names
        # the domain; sub-fields (mem ᵐ, temp ᶜ, watts ʷ) use unit-only.
        out="${out}${c}${w}${TM_UNIT}ʷ "
    fi
fi

# Trim trailing space, append reset.
out="${out% }"
[ -n "$out" ] && echo "${out}${TM_RESET}"
