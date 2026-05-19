#!/usr/bin/env bash
# Wrapper: host-level field selection for the generic gpu-amdgpu segment.
exec "$(dirname "$0")/../../segments/gpu-amdgpu.sh" -u -m -t
