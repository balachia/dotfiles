# Shared theme / color conventions for tmux status segments.
# Source this from each segment script (no shebang — it's a fragment).
#
# ── Glyph conventions (superscript lower for domain/unit labels) ──────────
#   ᶜ  CPU domain               ᶜ  celsius unit (contextual)
#   ᵐ  memory domain            ʷ  watts unit
#   ᵍ  GPU domain               ᵗ  throttle indicator (kernel thermal pressure)
#   ᵖ  power domain             ❋  Claude usage marker
#   △  AC / charging            ▽  battery / discharging
#
# Add a new domain → pick a non-colliding superscript-lower letter, add it
# here. Reserved: ᶜ ᵐ ᵍ ᵖ ʷ ᵗ.
#
# ── Color tiers (apply to data values; labels always TM_LABEL) ────────────

TM_LABEL="#[fg=colour1]"                          # red — domain markers (ᶜ ᵐ ᵍ ᵖ)
TM_UNIT="#[fg=colour0]"                           # cyan — unit symbols (ʷ ᶜ-celsius %)
TM_BASELINE="#[fg=colour8]"                       # dim — normal data
TM_WARN="#[fg=colour3]"                           # yellow — elevated
TM_WARN_HI="#[fg=colour11]"                       # bright yellow — high
TM_ALERT="#[fg=colour1,bold]"                     # red bold — danger
TM_BATTERY_AC="#[fg=colour2]"                     # green — on AC
TM_BATTERY_DC="#[fg=colour1]"                     # red — discharging
TM_THROTTLE_WARN="#[fg=colour0,bg=colour3,bold]"  # black on yellow — Moderate
TM_THROTTLE_ALERT="#[fg=colour0,bg=colour9,bold]" # black on bright-red — Heavy
TM_RESET="#[default]#[fg=colour8]"                # reset attrs, back to baseline
