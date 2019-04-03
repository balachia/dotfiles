#!/bin/sh

power_status () {
    if bluetoothctl show | grep -q "Powered: yes"; then return 0; else return 1; fi
}

scan_status () {
    if bluetoothctl show | grep -q "Discovering: yes"; then return 0; else return 1; fi
}

bluetooth_status () {
    x=$(bluetoothctl show)
    if echo "$x" | grep -q "Discovering: yes"; then
        class=scanning
    elif echo "$x" | grep -q "Powered: yes"; then
        class=power-on
    else
        class=power-off
    fi
}

case $1 in
    power-toggle)
        if power_status; then
            bluetoothctl power off > /dev/null
        else
            bluetoothctl power on > /dev/null
        fi
        pkill -RTMIN+10 waybar
        ;;
    scan-toggle)
        if scan_status; then
            bluetoothctl scan on & > /dev/null
        else
            bluetoothctl scan off & > /dev/null
        fi
        ;;
    *)
        bluetooth_status
        case $class in
            power-off)
                tt="Off (click to enable)";;
            power-on)
                tt="On (click to disable, right click to scan)";;
            scanning)
                tt="Scanning (right-click to stop scanning)";;
        esac
        #power_status && class=power-on || class=power-off
        #if bluetoothctl show | grep -q "Powered: yes"; then class=power-on; else class=power-off; fi
        printf "\n$tt\n$class\n"
        ;;
esac

