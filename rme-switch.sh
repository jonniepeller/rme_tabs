#!/bin/sh
# Test: switch which USB-connected RME device answers on http://172.20.0.1 (macOS).
#   ./rme-switch.sh              list network interfaces (find the RME ones)
#   ./rme-switch.sh en7 en8      enable en7, disable en8 (first = on, rest = off)

if [ $# -eq 0 ]; then
  networksetup -listallhardwareports | awk -F': ' '
    /^Hardware Port/ {name=$2} /^Device/ {dev=$2} /^Ethernet Address/ {print dev "\t" $2 "\t" name}' |
  while IFS="$(printf '\t')" read -r dev mac name; do
    ip=$(ifconfig "$dev" 2>/dev/null | awk '/inet /{print $2}')
    up=$(ifconfig "$dev" 2>/dev/null | grep -q 'status: active' && echo active || echo -)
    printf '%-6s %-18s %-8s %-15s %s\n' "$dev" "$mac" "$up" "${ip:--}" "$name"
  done
  exit
fi

on=$1; shift
for off in "$@"; do sudo ifconfig "$off" down; done
sudo ifconfig "$on" up
sudo arp -d 172.20.0.1 >/dev/null 2>&1

printf 'Waiting for %s' "$on"
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  r=$(curl -s -m 2 -X POST -H 'Content-Type: application/json' \
      -d '{"device":{"vendor_name":null,"model_name":null}}' \
      http://172.20.0.1/api/v2/self) && [ -n "$r" ] && break
  printf '.'; sleep 1
done
echo
echo "Device reply: ${r:-none (no answer on 172.20.0.1)}"
arp -n 172.20.0.1
