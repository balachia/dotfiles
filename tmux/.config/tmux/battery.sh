#!/bin/sh
pmset -g batt | awk '/[0-9]+%/{gsub(/;/,""); for(i=1;i<=NF;i++){if($i~/%/)p=$i; if($i=="charging"||$i=="charged")c="⚡"}} END{printf "%s%s",c,p}'
