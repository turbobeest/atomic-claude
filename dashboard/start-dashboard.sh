#!/usr/bin/env bash
#
# Start Tasks Dashboard Server and Open Browser
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${ATOMIC_TASKS_PORT:-5174}"

# Set ATOMIC_ROOT for this project
export ATOMIC_ROOT="${ATOMIC_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"

# Portable check: is something listening on $PORT?
_port_listening() {
    if command -v ss &>/dev/null; then
        ss -tlnH "sport = :$PORT" 2>/dev/null | grep -q LISTEN
    elif command -v lsof &>/dev/null; then
        lsof -Pi ":$PORT" -sTCP:LISTEN -t >/dev/null 2>&1
    elif command -v netstat &>/dev/null; then
        netstat -tln 2>/dev/null | grep -q ":$PORT "
    else
        # Last resort: try connecting
        (echo >/dev/tcp/localhost/$PORT) 2>/dev/null
    fi
}

# Portable: get PID of process on $PORT
_port_pid() {
    if command -v ss &>/dev/null; then
        ss -tlnpH "sport = :$PORT" 2>/dev/null | grep -oP 'pid=\K[0-9]+'  | head -1
    elif command -v lsof &>/dev/null; then
        lsof -ti ":$PORT" 2>/dev/null | head -1
    else
        echo ""
    fi
}

# Check if already running
if _port_listening; then
    # Dashboard is running - check if it's for this project
    RUNNING_ROOT=$(grep "Root:" "$SCRIPT_DIR/dashboard.log" 2>/dev/null | tail -1 | awk '{print $NF}')

    if [[ -n "$RUNNING_ROOT" ]] && [[ "$RUNNING_ROOT" != "$ATOMIC_ROOT" ]]; then
        echo "⚠ Dashboard running for different project, restarting..."
        DASH_PID=$(_port_pid)
        if [[ -n "$DASH_PID" ]]; then
            kill "$DASH_PID" 2>/dev/null || true
            sleep 1
        fi
    else
        echo "✓ Dashboard already running on port $PORT"
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
    if _port_listening; then
        echo "✓ Dashboard server started (PID: $SERVER_PID)"
        break
    fi
    sleep 0.5
done

# Open browser (detached from this process)
(
    sleep 1
    bash "$SCRIPT_DIR/open-dashboard.sh"
) >/dev/null 2>&1 &

echo "✓ Dashboard available at: http://localhost:$PORT"
echo "  Opening browser window..."
