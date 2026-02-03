#!/usr/bin/env bash
#
# Open Tasks Dashboard as a minimal popup window
#

PORT="${ATOMIC_TASKS_PORT:-5173}"
URL="http://localhost:$PORT"

# Detect OS and open as app window
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - open as app with minimal chrome
    open -na "Google Chrome" --args \
        --app="$URL" \
        --window-size=1250,900 \
        --window-position=100,100
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux - open in Chrome app mode
    google-chrome --app="$URL" --window-size=1250,900 &
else
    # Windows or fallback
    start chrome --app="$URL" --window-size=1250,900
fi

echo "✓ Dashboard opened as popup window"
