#!/usr/bin/env bash
#
# Open Tasks Dashboard as a minimal popup window
#

PORT="${ATOMIC_TASKS_PORT:-5174}"
URL="http://localhost:$PORT"

# Detect OS and open as app window
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - try multiple approaches for maximum compatibility

    # Method 1: Try Chrome app mode via open command
    if nohup open -na "Google Chrome" --args \
        --app="$URL" \
        --window-size=1250,900 \
        --window-position=100,100 </dev/null >/dev/null 2>&1 &
    then
        echo "✓ Dashboard opened in Chrome app mode"
    # Method 2: Try AppleScript (more reliable from subprocesses)
    elif osascript -e "tell application \"Google Chrome\" to open location \"$URL\"" -e "tell application \"Google Chrome\" to activate" </dev/null >/dev/null 2>&1; then
        echo "✓ Dashboard opened in Chrome via AppleScript"
    # Method 3: Fallback to default browser
    else
        nohup open "$URL" </dev/null >/dev/null 2>&1 &
        echo "✓ Dashboard opened in default browser"
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux - open in Chrome app mode with nohup
    if command -v google-chrome &>/dev/null; then
        nohup google-chrome --app="$URL" --window-size=1250,900 </dev/null >/dev/null 2>&1 &
        echo "✓ Dashboard opened in Chrome app mode"
    else
        nohup xdg-open "$URL" </dev/null >/dev/null 2>&1 &
        echo "✓ Dashboard opened in default browser"
    fi
else
    # Windows or fallback
    nohup start chrome --app="$URL" --window-size=1250,900 </dev/null >/dev/null 2>&1 || nohup start "$URL" </dev/null >/dev/null 2>&1 &
    echo "✓ Dashboard opened"
fi
