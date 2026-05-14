#!/bin/sh
# ▴ (green) on AC / charging, ▾ (red) when discharging on battery
pmset -g batt | awk '
NR==1 {
    if (/AC Power/) { color = "#[fg=colour2]"; arrow = "△" }
    else            { color = "#[fg=colour1]"; arrow = "▽" }
}
/[0-9]+%/ {
    for (i=1; i<=NF; i++) if ($i ~ /%/) { gsub(/;/, "", $i); pct = $i }
}
END { printf "%s%s#[default]#[fg=colour8]%s", color, arrow, pct }
'
