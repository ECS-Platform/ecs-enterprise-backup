#!/bin/bash
# Capture ECS governance dashboard screenshots with headless Chrome.
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUT="demo-data/screenshots"
mkdir -p "$OUT"
pkill -9 -f "headless=new" 2>/dev/null
rm -rf /tmp/cr-shoot-* 2>/dev/null

shoot () {
  local name="$1" url="$2"
  rm -rf "/tmp/cr-shoot-$name"
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --no-sandbox \
    --no-first-run --no-default-browser-check --virtual-time-budget=8000 \
    --force-device-scale-factor=1 --window-size=1500,1500 \
    --user-data-dir="/tmp/cr-shoot-$name" \
    --screenshot="$OUT/$name.png" "$url" >/dev/null 2>&1 &
  local pid=$!
  local waited=0
  while kill -0 "$pid" 2>/dev/null; do
    sleep 1; waited=$((waited+1))
    if [ -s "$OUT/$name.png" ] && [ "$waited" -ge 4 ]; then kill -9 "$pid" 2>/dev/null; break; fi
    if [ "$waited" -ge 15 ]; then kill -9 "$pid" 2>/dev/null; break; fi
  done
  wait "$pid" 2>/dev/null
  echo "$name.png -> $(stat -f%z "$OUT/$name.png" 2>/dev/null || echo MISSING) bytes"
}

B="http://localhost:8000/mvp/platform"
for spec in "$@"; do
  name="${spec%%::*}"; path="${spec#*::}"
  shoot "$name" "$B$path"
done
pkill -9 -f "headless=new" 2>/dev/null
echo COMPLETE
