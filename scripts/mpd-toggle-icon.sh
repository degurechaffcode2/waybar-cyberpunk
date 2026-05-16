#!/bin/bash
state=$(mpc status 2>/dev/null | grep -oP '\[\w+\]' | head -1)
case "$state" in
    "[playing]") echo "󰏤" ;;
    "[paused]")  echo "󰐊" ;;
    *)           echo "󰓛" ;;
esac
