#!/usr/bin/env bash
# AMD package power for tmux statusline (amdgpu hwmon power1_average).
#
# On discrete cards this is the card TBP — just the GPU. On APUs (Strix Halo,
# Phoenix, etc.) this is PPT — the whole package envelope: CPU + iGPU + IF +
# memctl. We don't distinguish here; the glyph (ᵖ = power domain) reads
# accurately either way. Host wrappers can carry the per-host semantics in
# their comment header if it matters.
#
# Without root we can't reach RAPL energy counters (CVE-2020-8694 mitigation),
# so this is the only userspace power signal AMD systems expose.
#
# Silent (exit 0) if no amdgpu card with power1_average is found.

source "$HOME/.config/tmux/theme.sh"

card_hwmon=""
for c in /sys/class/drm/card[0-9]*; do
    [ -e "$c/device/gpu_busy_percent" ] || continue
    for h in "$c"/device/hwmon/hwmon*; do
        [ "$(cat "$h/name" 2>/dev/null)" = "amdgpu" ] && { card_hwmon="$h"; break 2; }
    done
done
[ -n "$card_hwmon" ] || exit 0

w_uw=$(cat "$card_hwmon/power1_average" 2>/dev/null)
[ -n "$w_uw" ] || exit 0
w=$(( w_uw / 1000000 ))

# Absolute tiers; per-host peaks vary too widely (Strix Halo PPT ~30-150W vs
# 9070 XT TBP 20-304W) for shared auto-calibration to be meaningful.
if   [ "$w" -ge 200 ]; then c="$TM_ALERT"
elif [ "$w" -ge 100 ]; then c="$TM_WARN_HI"
elif [ "$w" -ge 50 ];  then c="$TM_WARN"
else                       c="$TM_BASELINE"
fi

echo "${TM_LABEL}ᵖ${c}${w}${TM_UNIT}ʷ${TM_RESET}"
