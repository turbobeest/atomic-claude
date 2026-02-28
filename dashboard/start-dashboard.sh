#!/usr/bin/env bash
#
# Start Tasks Dashboard Server and Browser Sub-Apps
#
# Features:
# - Calls stop-dashboard.sh first to kill stale processes
# - Writes PID files to .state/dashboard/ for reliable cleanup
# - Uses setsid for sub-apps (own process group for clean kill)
# - Waits for each process to be ready before continuing
# - Binds sub-apps to 0.0.0.0 for remote access
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${ATOMIC_TASKS_PORT:-5174}"

# Set ATOMIC_ROOT (where atomic-claude code lives)
export ATOMIC_ROOT="${ATOMIC_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"

# Detect PROJECT_ROOT: if .state/ or .outputs/ exist in parent, use parent
# (This handles atomic-claude deployed in a host project like CUI-ENGAGEMENT-MANAGER/atomic-claude)
if [[ -d "$ATOMIC_ROOT/.state" ]]; then
    PROJECT_ROOT="$ATOMIC_ROOT"
elif [[ -d "$(dirname "$ATOMIC_ROOT")/.state" ]] || [[ -d "$(dirname "$ATOMIC_ROOT")/.outputs" ]]; then
    PROJECT_ROOT="$(cd "$ATOMIC_ROOT/.." && pwd)"
else
    PROJECT_ROOT="$ATOMIC_ROOT"
fi

PID_DIR="$PROJECT_ROOT/.state/dashboard"

# --- Stop any existing dashboard processes first ---
STOP_SCRIPT="$SCRIPT_DIR/stop-dashboard.sh"
if [[ -x "$STOP_SCRIPT" ]]; then
    bash "$STOP_SCRIPT"
    echo ""
fi

# Create PID directory
mkdir -p "$PID_DIR"

# Portable check: is something listening on a given port?
_port_listening() {
    local p="$1"
    if command -v ss &>/dev/null; then
        ss -tlnH "sport = :$p" 2>/dev/null | grep -q LISTEN
    elif command -v lsof &>/dev/null; then
        lsof -Pi ":$p" -sTCP:LISTEN -t >/dev/null 2>&1
    elif command -v netstat &>/dev/null; then
        netstat -tln 2>/dev/null | grep -q ":$p "
    else
        (echo >/dev/tcp/127.0.0.1/$p) 2>/dev/null
    fi
}

# Wait for a port to start listening (with timeout)
_wait_for_port() {
    local p="$1" timeout_secs="${2:-5}" name="${3:-service}"
    local i=0
    local max=$((timeout_secs * 2))
    while [[ $i -lt $max ]]; do
        if _port_listening "$p"; then
            return 0
        fi
        sleep 0.5
        i=$((i + 1))
    done
    echo "  ! $name did not start within ${timeout_secs}s"
    return 1
}

# --- Start main dashboard ---

# Install dependencies if needed
if [[ ! -d "$SCRIPT_DIR/node_modules" ]]; then
    echo "Installing dashboard dependencies..."
    cd "$SCRIPT_DIR"
    npm install --silent
fi

# Start server in background
cd "$SCRIPT_DIR"
nohup node server.js > "$SCRIPT_DIR/dashboard.log" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_DIR/main.pid"

# Wait for main dashboard to be ready
if _wait_for_port "$PORT" 5 "Main dashboard"; then
    echo "Dashboard server started (PID: $SERVER_PID, port $PORT)"
fi

# --- Start browser sub-apps ---

_start_subapp() {
    local name="$1" dir="$2" port="$3" pidname="$4"

    # Verify directory and package.json exist
    if [[ ! -d "$dir" ]]; then
        echo "  ! $name directory not found: $dir"
        return 1
    fi
    if [[ ! -f "$dir/package.json" ]]; then
        echo "  ! $name missing package.json, skipping"
        return 1
    fi

    # Install dependencies if needed
    if [[ ! -d "$dir/node_modules" ]]; then
        echo "  Installing $name dependencies..."
        (cd "$dir" && npm install --silent 2>/dev/null) || { echo "  ! $name npm install failed"; return 1; }
    fi

    # Start dev server, bind all interfaces for remote access
    # Use setsid on Linux, plain background on macOS (setsid not available)
    cd "$dir"
    if command -v setsid &>/dev/null; then
        setsid nohup npx vite dev --port "$port" --host 0.0.0.0 > "$dir/dev.log" 2>&1 &
    else
        # macOS: use nohup without setsid
        nohup npx vite dev --port "$port" --host 0.0.0.0 > "$dir/dev.log" 2>&1 &
    fi
    local pid=$!
    echo "$pid" > "$PID_DIR/${pidname}.pid"

    # Wait for sub-app to be ready
    if _wait_for_port "$port" 10 "$name"; then
        echo "  $name started (PID: $pid, port $port)"
    fi
}

echo ""
echo "Starting browser sub-apps..."
_start_subapp "Agent Manager"  "$ATOMIC_ROOT/agents/agent-manager"  5175 agents
_start_subapp "Audit Browser"  "$ATOMIC_ROOT/audits/audit-browser"  5176 audits
_start_subapp "Skills Browser" "$ATOMIC_ROOT/skills/skills-browser"  5177 skills

# Open browser (detached from this process)
(
    sleep 1
    bash "$SCRIPT_DIR/open-dashboard.sh"
) >/dev/null 2>&1 &

echo ""
echo "Dashboard available at: http://127.0.0.1:$PORT"
echo "  Sub-apps: Agents(:5175) Audits(:5176) Skills(:5177)"
echo "  PID files: $PID_DIR/"
