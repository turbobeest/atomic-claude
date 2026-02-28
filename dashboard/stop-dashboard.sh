#!/usr/bin/env bash
#
# Stop all dashboard processes (main server + browser sub-apps)
#
# Reads PID files from .state/dashboard/ and kills process groups.
# Falls back to port-based detection if PID files are stale.
# Idempotent — safe to call even if nothing is running.
#

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ATOMIC_ROOT="${ATOMIC_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"

# Detect PROJECT_ROOT: if .state/ or .outputs/ exist in parent, use parent
if [[ -d "$ATOMIC_ROOT/.state" ]]; then
    PROJECT_ROOT="$ATOMIC_ROOT"
elif [[ -d "$(dirname "$ATOMIC_ROOT")/.state" ]] || [[ -d "$(dirname "$ATOMIC_ROOT")/.outputs" ]]; then
    PROJECT_ROOT="$(cd "$ATOMIC_ROOT/.." && pwd)"
else
    PROJECT_ROOT="$ATOMIC_ROOT"
fi

PID_DIR="$PROJECT_ROOT/.state/dashboard"

PORT_MAIN="${ATOMIC_TASKS_PORT:-5174}"
PORT_AGENTS=5175
PORT_AUDITS=5176
PORT_SKILLS=5177

STOPPED=0

# Kill a process by PID file, targeting the whole process group
_kill_pidfile() {
    local name="$1" pidfile="$2"
    [[ ! -f "$pidfile" ]] && return 1

    local pid
    pid=$(<"$pidfile")

    # Validate PID is numeric and process exists
    if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
        # Get process group ID and kill the whole group
        local pgid
        pgid=$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ')
        if [[ -n "$pgid" && "$pgid" != "0" ]]; then
            kill -- -"$pgid" 2>/dev/null || kill "$pid" 2>/dev/null
        else
            kill "$pid" 2>/dev/null
        fi
        echo "  Stopped $name (PID $pid)"
        STOPPED=$((STOPPED + 1))
    fi

    rm -f "$pidfile"
    return 0
}

# Fallback: kill whatever is listening on a port
_kill_port() {
    local name="$1" port="$2"

    local pid=""
    if command -v ss &>/dev/null; then
        pid=$(ss -tlnpH "sport = :$port" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | head -1)
    elif command -v lsof &>/dev/null; then
        pid=$(lsof -ti ":$port" 2>/dev/null | head -1)
    fi

    if [[ -n "$pid" ]]; then
        local pgid
        pgid=$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ')
        if [[ -n "$pgid" && "$pgid" != "0" ]]; then
            kill -- -"$pgid" 2>/dev/null || kill "$pid" 2>/dev/null
        else
            kill "$pid" 2>/dev/null
        fi
        echo "  Stopped $name on port $port (PID $pid, fallback)"
        STOPPED=$((STOPPED + 1))
        return 0
    fi
    return 1
}

echo "Stopping dashboard processes..."

# Try PID files first, then fall back to port-based kill
_kill_pidfile "Main dashboard" "$PID_DIR/main.pid"    || _kill_port "Main dashboard" "$PORT_MAIN"
_kill_pidfile "Agent Manager"  "$PID_DIR/agents.pid"  || _kill_port "Agent Manager"  "$PORT_AGENTS"
_kill_pidfile "Audit Browser"  "$PID_DIR/audits.pid"  || _kill_port "Audit Browser"  "$PORT_AUDITS"
_kill_pidfile "Skills Browser" "$PID_DIR/skills.pid"  || _kill_port "Skills Browser" "$PORT_SKILLS"

# Brief wait for processes to exit, then check for stragglers
if [[ $STOPPED -gt 0 ]]; then
    sleep 0.5
fi

# Clean up any remaining PID files
rm -f "$PID_DIR"/*.pid 2>/dev/null

if [[ $STOPPED -gt 0 ]]; then
    echo "Stopped $STOPPED process(es)."
else
    echo "No dashboard processes were running."
fi
