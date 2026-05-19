#!/usr/bin/env bash
# duma is Strix Halo APU — amdgpu power1 = PPT (whole package: CPU + iGPU +
# IF + memctl), which is the most useful single power signal on this host.
exec "$(dirname "$0")/../../segments/power-amdgpu.sh"
