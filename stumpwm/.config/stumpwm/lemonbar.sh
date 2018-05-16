#!/bin/sh

echo "%{T-}"

echo "%{c}Welcome"
sleep 1

while true; do
        echo "%{c}%{T1} $(date) "
        sleep 1
done
