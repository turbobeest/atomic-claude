#!/usr/bin/env bash
#
# Start Tasks Dashboard Server and Open Browser
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${ATOMIC_TASKS_PORT:-5174}"

# Set ATOMIC_ROOT for this project
export ATOMIC_ROOT="${ATOMIC_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"

# Check if already running
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    # Dashboard is running - check if it's for this project
    # Get the project name from current ATOMIC_ROOT
    CURRENT_PROJECT=$(basename "$ATOMIC_ROOT")

    # Try to determine what project the running dashboard is serving
    # by checking the dashboard.log for ATOMIC_ROOT
    RUNNING_ROOT=$(grep "Root:" "$SCRIPT_DIR/dashboard.log" 2>/dev/null | tail -1 | awk '{print $NF}')

    if [[ -n "$RUNNING_ROOT" ]] && [[ "$RUNNING_ROOT" != "$ATOMIC_ROOT" ]]; then
        echo "⚠ Dashboard running for different project, restarting..."
        # Kill existing dashboard
        DASH_PID=$(lsof -ti :$PORT)
        kill $DASH_PID 2>/dev/null || true
        sleep 1
    else
        echo "✓ Dashboard already running on port $PORT"
        # Just open browser
        bash "$SCRIPT_DIR/open-dashboard.sh" 2>/dev/null || true
        exit 0
    fi
fi

# Check if node_modules exists
if [[ ! -d "$SCRIPT_DIR/node_modules" ]]; then
    echo "⚙ Installing dashboard dependencies..."
    cd "$SCRIPT_DIR"
    npm install --silent
fi

# Start server in background
cd "$SCRIPT_DIR"
nohup node server.js > "$SCRIPT_DIR/dashboard.log" 2>&1 &
SERVER_PID=$!

# Wait for server to start
for i in {1..10}; do
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "✓ Dashboard server started (PID: $SERVER_PID)"
        break
    fi
    sleep 0.5
done

# Open browser (detached from this process)
sleep 1  # Give server moment to fully initialize

# Launch browser opening in background, fully detached
(
    sleep 0.5  # Brief delay to ensure server is responsive
    bash "$SCRIPT_DIR/open-dashboard.sh"
) >/dev/null 2>&1 &

echo "✓ Dashboard available at: http://localhost:$PORT"
echo "  Opening browser window..."
