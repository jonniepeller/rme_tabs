#!/bin/bash
# Build RME Tabs.app, replace any installed copy (quitting it if running) and launch it. See README.md.
set -euo pipefail
cd "$(dirname "$0")"

APP='RME Tabs'
INSTALLED="/Applications/$APP.app"

if [ ! -x .venv/bin/pyinstaller ]; then
    echo '==> Setting up .venv'
    python3 -m venv .venv
    .venv/bin/pip install --quiet rumps pyinstaller
fi

echo '==> Building'
.venv/bin/pyinstaller --noconfirm --log-level WARN app.spec

if pgrep -xq "$APP"; then
    echo '==> Quitting the running app'
    osascript -e "quit app \"$APP\""
    for _ in {1..20}; do pgrep -xq "$APP" || break; sleep 0.25; done
    pkill -x "$APP" || true
fi

echo "==> Installing to $INSTALLED"
rm -rf "$INSTALLED"
ditto "dist/$APP.app" "$INSTALLED"

echo '==> Launching'
open "$INSTALLED"
