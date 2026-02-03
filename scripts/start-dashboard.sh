#!/usr/bin/env bash
#
# Start the ATOMIC CLAUDE Tasks Dashboard
#

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DASHBOARD_DIR="$ROOT_DIR/tasks-dashboard"

# Check if Node.js is installed
if ! command -v node &>/dev/null; then
    echo "Error: Node.js is required but not installed"
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

# Check if dependencies are installed
if [[ ! -d "$DASHBOARD_DIR/node_modules" ]]; then
    echo "Installing dashboard dependencies..."
    cd "$DASHBOARD_DIR"
    npm install
fi

# Export ATOMIC_ROOT for the server
export ATOMIC_ROOT="$ROOT_DIR"

# Start the server
echo ""
echo "Starting ATOMIC CLAUDE Tasks Dashboard..."
cd "$DASHBOARD_DIR"
exec node server.js
