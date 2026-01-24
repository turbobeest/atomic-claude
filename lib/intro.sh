#!/bin/bash
#
# ATOMIC CLAUDE - Retro Terminal Intro
# WarGames-style typing animation
#

# ─────────────────────────────────────────────────────────────────────────────
# CROSS-PLATFORM TERMINAL DETECTION
# ─────────────────────────────────────────────────────────────────────────────

# Detect if we're in a real terminal with ANSI support
_detect_terminal_capabilities() {
    # Check if stdout is a terminal
    if [[ ! -t 1 ]]; then
        export TERM_HAS_COLORS=false
        export TERM_HAS_TPUT=false
        return
    fi

    # Check for Windows native terminals (CMD, PowerShell without ANSI)
    case "${TERM:-dumb}" in
        dumb|unknown|"")
            export TERM_HAS_COLORS=false
            export TERM_HAS_TPUT=false
            return
            ;;
    esac

    # Check if tput is available and works
    if command -v tput >/dev/null 2>&1 && tput cols >/dev/null 2>&1; then
        export TERM_HAS_TPUT=true
    else
        export TERM_HAS_TPUT=false
    fi

    # Most modern terminals support ANSI colors
    export TERM_HAS_COLORS=true
}

# Initialize terminal capabilities
_detect_terminal_capabilities

# Terminal colors - that green CRT glow (with fallback for no-color terminals)
if [[ "${TERM_HAS_COLORS:-true}" == "true" ]]; then
    WOPR_GREEN='\033[0;32m'
    WOPR_BRIGHT='\033[1;32m'
    WOPR_DIM='\033[2;32m'
    WOPR_BLINK='\033[5;32m'
    NC='\033[0m'
else
    WOPR_GREEN=''
    WOPR_BRIGHT=''
    WOPR_DIM=''
    WOPR_BLINK=''
    NC=''
fi

# Typing speed (seconds between characters)
TYPING_SPEED=0.04
TYPING_SPEED_FAST=0.02
TYPING_SPEED_1200BAUD=0.08  # That slow modem feel
LINE_PAUSE=0.5
DRAMATIC_PAUSE=1.5

# Type text character by character
wopr_type() {
    local text="$1"
    local speed="${2:-$TYPING_SPEED}"

    for (( i=0; i<${#text}; i++ )); do
        printf "%s" "${text:$i:1}"
        sleep "$speed"
    done
}

# Type a line and add newline
wopr_line() {
    local text="$1"
    local speed="${2:-$TYPING_SPEED}"

    echo -ne "${WOPR_BRIGHT}"
    wopr_type "$text" "$speed"
    echo -e "${NC}"
    sleep "$LINE_PAUSE"
}

# Fast type (for less dramatic moments)
wopr_fast() {
    wopr_line "$1" "$TYPING_SPEED_FAST"
}

# Blinking cursor effect
wopr_cursor() {
    local duration="${1:-3}"
    local end_time=$((SECONDS + duration))

    while [ $SECONDS -lt $end_time ]; do
        echo -ne "${WOPR_BRIGHT}█${NC}"
        sleep 0.5
        echo -ne "\b "
        sleep 0.5
        echo -ne "\b"
    done
}

# Clear screen with retro effect
wopr_clear() {
    # Quick scan-line clear effect (with cross-platform fallback)
    if [[ "${TERM_HAS_TPUT:-false}" == "true" ]]; then
        local lines=$(tput lines 2>/dev/null || echo 24)
        local cols=$(tput cols 2>/dev/null || echo 80)
        for ((i=0; i<lines; i++)); do
            tput cup $i 0 2>/dev/null
            echo -ne "${WOPR_DIM}"
            printf '%*s' "$cols" '' | tr ' ' '░'
            echo -ne "${NC}"
            sleep 0.01
        done
    fi
    # Use clear command or ANSI escape sequence
    if command -v clear >/dev/null 2>&1; then
        clear
    else
        # ANSI escape: clear screen and move cursor to home
        printf '\033[2J\033[H'
    fi
}

# The main intro sequence
wopr_intro() {
    clear
    echo ""
    sleep 0.5

    # Connection sequence - nice and slow like 1200 baud
    echo -ne "${WOPR_DIM}"
    wopr_type "CONNECTING TO MAINFRAME" "$TYPING_SPEED_1200BAUD"
    for i in {1..3}; do
        sleep 0.4
        echo -n "."
    done
    echo -e "${NC}"
    sleep "$DRAMATIC_PAUSE"

    echo ""

    # The classic greeting - slow 1200 baud style
    echo -ne "${WOPR_BRIGHT}"
    wopr_type "GREETINGS PROFESSOR FALKEN." "$TYPING_SPEED_1200BAUD"
    echo -e "${NC}"

    sleep "$DRAMATIC_PAUSE"
    echo ""

    # The chess question - also slow
    echo -ne "${WOPR_BRIGHT}"
    wopr_type "HOW ABOUT A NICE GAME OF CHESS?" "$TYPING_SPEED_1200BAUD"
    echo -e "${NC}"

    sleep "$DRAMATIC_PAUSE"
    echo ""
    echo ""

    # Transition to ATOMIC CLAUDE
    echo -ne "${WOPR_DIM}"
    wopr_type "..." 0.4
    echo -e "${NC}"
    sleep "$DRAMATIC_PAUSE"

    echo -ne "${WOPR_BRIGHT}"
    wopr_type "JUST KIDDING." "$TYPING_SPEED_1200BAUD"
    echo -e "${NC}"
    sleep "$LINE_PAUSE"

    echo ""
    echo -ne "${WOPR_BRIGHT}"
    wopr_type "LET'S BUILD SOMETHING INSTEAD." "$TYPING_SPEED_1200BAUD"
    echo -e "${NC}"

    sleep "$DRAMATIC_PAUSE"
    clear

    # ASCII Art title with mini atom
    echo ""
    echo -e "${WOPR_BRIGHT}"
    cat << 'EOF'
        ██               █████╗ ████████╗ ██████╗ ███╗   ███╗██╗ ██████╗
    ████  ████          ██╔══██╗╚══██╔══╝██╔═══██╗████╗ ████║██║██╔════╝
  ████  ██  ████        ███████║   ██║   ██║   ██║██╔████╔██║██║██║
  ████  ██  ████        ██╔══██║   ██║   ██║   ██║██║╚██╔╝██║██║██║
    ████  ████          ██║  ██║   ██║   ╚██████╔╝██║ ╚═╝ ██║██║╚██████╗
        ██              ╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝╚═╝ ╚═════╝

                         ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗
                        ██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝
                        ██║     ██║     ███████║██║   ██║██║  ██║█████╗
                        ██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝
                        ╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗
                         ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝
EOF
    echo -e "${NC}"

    sleep "$DRAMATIC_PAUSE"
    echo ""

    # Tagline
    echo -ne "    ${WOPR_DIM}"
    wopr_type "Script-controlled LLM invocations" "$TYPING_SPEED_FAST"
    echo -e "${NC}"
    echo -ne "    ${WOPR_DIM}"
    wopr_type "for deterministic software development" "$TYPING_SPEED_FAST"
    echo -e "${NC}"

    sleep "$LINE_PAUSE"
    echo ""

    # Brief intro
    echo -e "${WOPR_DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "    ${WOPR_DIM}ATOMIC CLAUDE guides you through a 10-phase pipeline:${NC}"
    echo -e "    ${WOPR_DIM}Setup → Discovery → PRD → Tasks → Spec → Build → Review →${NC}"
    echo -e "    ${WOPR_DIM}Integration → Deployment Prep → Release${NC}"
    echo ""
    echo -e "    ${WOPR_DIM}You stay in control. The script orchestrates; Claude assists.${NC}"
    echo ""

    # System info
    echo -e "${WOPR_DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    echo -ne "    ${WOPR_GREEN}"
    wopr_type "SYSTEM STATUS: " "$TYPING_SPEED_FAST"
    echo -ne "${WOPR_BRIGHT}ONLINE${NC}"
    echo ""

    echo -ne "    ${WOPR_GREEN}"
    wopr_type "MODE: " "$TYPING_SPEED_FAST"
    echo -ne "${WOPR_BRIGHT}PHASE 0 - SETUP${NC}"
    echo ""

    echo -ne "    ${WOPR_GREEN}"
    wopr_type "PRINCIPLE: " "$TYPING_SPEED_FAST"
    echo -ne "${WOPR_BRIGHT}SCRIPT IS SOVEREIGN${NC}"
    echo ""

    echo ""
    echo -e "${WOPR_DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    sleep "$LINE_PAUSE"
    echo ""
    echo -ne "    ${WOPR_DIM}"
    wopr_type "Press ENTER to begin..." "$TYPING_SPEED_FAST"
    echo -ne "${NC}"
    wopr_cursor 2
    read -r

    clear
}

# Quick intro (skip the WarGames part)
wopr_intro_quick() {
    clear
    echo ""
    echo -e "${WOPR_BRIGHT}"
    cat << 'EOF'
        ██               █████╗ ████████╗ ██████╗ ███╗   ███╗██╗ ██████╗
    ████  ████          ██╔══██╗╚══██╔══╝██╔═══██╗████╗ ████║██║██╔════╝
  ████  ██  ████        ███████║   ██║   ██║   ██║██╔████╔██║██║██║
  ████  ██  ████        ██╔══██║   ██║   ██║   ██║██║╚██╔╝██║██║██║
    ████  ████          ██║  ██║   ██║   ╚██████╔╝██║ ╚═╝ ██║██║╚██████╗
        ██              ╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝╚═╝ ╚═════╝

                         ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗
                        ██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝
                        ██║     ██║     ███████║██║   ██║██║  ██║█████╗
                        ██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝
                        ╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗
                         ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝
EOF
    echo -e "${NC}"
    echo ""
    echo -e "        ${WOPR_DIM}Script-controlled LLM invocations${NC}"
    echo -e "        ${WOPR_DIM}for deterministic software development${NC}"
    echo ""
    sleep 1
}

# Export for use in other scripts
export -f wopr_type wopr_line wopr_fast wopr_cursor wopr_clear wopr_intro wopr_intro_quick
