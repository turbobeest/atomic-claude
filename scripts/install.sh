#!/usr/bin/env bash
#
# Atomic Claude 2.0 - Installation Helper Script
#
# Helps set up the development environment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check_python() {
    print_header "Checking Python Installation"

    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f2)

    print_success "Python $PYTHON_VERSION found"

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
        print_error "Python 3.9+ required (found $PYTHON_VERSION)"
        exit 1
    fi
}

check_env_file() {
    print_header "Checking Environment Configuration"

    if [ -f "$PROJECT_ROOT/.env" ]; then
        print_success ".env file exists"
    else
        print_warning ".env file not found"
        print_info "Creating .env from .env.example"
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        print_warning "Please edit .env and configure your LLM provider"
    fi
}

install_package() {
    print_header "Installing Package"

    cd "$PROJECT_ROOT"

    # Check if we should install dev dependencies
    if [ "${1:-}" == "--dev" ]; then
        print_info "Installing with development dependencies"
        pip install -e ".[dev]"
    else
        print_info "Installing package (production mode)"
        print_info "Use './scripts/install.sh --dev' for development dependencies"
        pip install -e .
    fi

    print_success "Package installed"
}

verify_installation() {
    print_header "Verifying Installation"

    cd "$PROJECT_ROOT"
    python scripts/verify_package.py
}

print_next_steps() {
    print_header "Installation Complete!"

    echo ""
    echo "Next steps:"
    echo ""
    echo "  1. Configure your environment:"
    echo "     ${GREEN}vi .env${NC}"
    echo ""
    echo "  2. Check the status:"
    echo "     ${GREEN}python main.py status${NC}"
    echo ""
    echo "  3. Run Phase 0 (Setup):"
    echo "     ${GREEN}python main.py run 0${NC}"
    echo ""
    echo "  4. Run tests:"
    echo "     ${GREEN}pytest${NC}"
    echo ""
    echo "  5. Run UAT:"
    echo "     ${GREEN}./test/run_uat.sh${NC}"
    echo ""
}

main() {
    print_header "Atomic Claude 2.0 - Installation"

    # Run checks and installation
    check_python
    check_env_file
    install_package "$@"
    verify_installation
    print_next_steps
}

# Run main function with all arguments
main "$@"
